"""
src/training/train_supervised.py
─────────────────────────────────
Supervised fine-tuning of ShadowLitterNet on the synthetic dump dataset.
Combined Dice + BCE loss, full augmentation, TensorBoard logging.
"""
from __future__ import annotations
import logging, random
from pathlib import Path
import numpy as np
import torch, torch.nn as nn
from torch.utils.data import Dataset, DataLoader, Subset
from torch.utils.tensorboard import SummaryWriter
import yaml
from src.models.siamese_unet import ShadowLitterNet

logger = logging.getLogger(__name__)

class DiceBCELoss(nn.Module):
    def __init__(self, dw=0.5, bw=0.5):
        super().__init__(); self.dw=dw; self.bw=bw
        self.bce = nn.BCEWithLogitsLoss()
    def forward(self, logits, targets):
        cl = logits[:,1]; tf = targets.float()
        bce = self.bce(cl, tf)
        p = torch.sigmoid(cl)
        inter = (p*tf).sum((1,2)); denom = p.sum((1,2))+tf.sum((1,2))
        dice = (1-(2*inter+1)/(denom+1)).mean()
        return self.bw*bce + self.dw*dice

def augment(t1, t2, mask):
    if random.random()>0.5: t1,t2,mask = t1[:,:,::-1].copy(),t2[:,:,::-1].copy(),mask[:,::-1].copy()
    if random.random()>0.5: t1,t2,mask = t1[:,::-1].copy(),t2[:,::-1].copy(),mask[::-1].copy()
    k=random.randint(0,3)
    if k: t1=np.rot90(t1,k,(1,2)).copy(); t2=np.rot90(t2,k,(1,2)).copy(); mask=np.rot90(mask,k).copy()
    return t1, t2, mask

class SiamesePatchDataset(Dataset):
    def __init__(self, d, aug=False):
        self.aug=aug
        self.samples=sorted(Path(d).glob("*_image.npy"))
        if not self.samples: raise FileNotFoundError(d)
    def __len__(self): return len(self.samples)
    def __getitem__(self, i):
        p=self.samples[i]
        t2=np.load(p).astype(np.float32)
        mp=Path(str(p).replace("_image.npy","_mask.npy"))
        mask=np.load(mp).astype(np.uint8) if mp.exists() else np.zeros(t2.shape[1:],np.uint8)
        t1=np.clip(t2+np.random.normal(0,0.01,t2.shape).astype(np.float32),0,1)
        if self.aug: t1,t2,mask=augment(t1,t2,mask)
        return torch.from_numpy(t1),torch.from_numpy(t2),torch.from_numpy(mask.astype(np.int64))

def iou(pred, tgt): i=(pred&tgt.bool()).sum().float(); u=(pred|tgt.bool()).sum().float(); return (i/(u+1e-8)).item()
def f1(pred, tgt):
    tp=(pred&tgt.bool()).sum().float(); fp=(pred&~tgt.bool()).sum().float(); fn=(~pred&tgt.bool()).sum().float()
    p=tp/(tp+fp+1e-8); r=tp/(tp+fn+1e-8); return (2*p*r/(p+r+1e-8)).item()

def train_supervised(config_path="configs/siamese_config.yaml"):
    cfg=yaml.safe_load(open(config_path)); tr=cfg["training"]
    torch.manual_seed(tr["seed"]); random.seed(tr["seed"]); np.random.seed(tr["seed"])
    device=torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Device: {device}")

    data_dir=cfg["data"]["synthetic_dir"]
    n=len(list(Path(data_dir).glob("*_image.npy")))
    nt=int(n*cfg["data"]["train_ratio"]); nv=int(n*cfg["data"]["val_ratio"])
    idx=list(range(n)); random.shuffle(idx)
    train_ds=Subset(SiamesePatchDataset(data_dir,aug=True), idx[:nt])
    val_ds  =Subset(SiamesePatchDataset(data_dir,aug=False),idx[nt:nt+nv])
    TL=DataLoader(train_ds,batch_size=tr["batch_size"],shuffle=True,num_workers=4,pin_memory=True)
    VL=DataLoader(val_ds,  batch_size=tr["batch_size"],shuffle=False,num_workers=4,pin_memory=True)

    model=ShadowLitterNet(cfg["model"]["in_channels"],cfg["model"]["num_classes"],cfg["model"]["pretrained"]).to(device)
    opt_c=cfg["optimizer"]
    optimizer=torch.optim.AdamW(model.parameters(),lr=opt_c["lr"],weight_decay=opt_c["weight_decay"])
    sc=cfg["scheduler"]
    scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,T_max=sc["t_max"],eta_min=sc["eta_min"])
    criterion=DiceBCELoss(cfg["loss"]["dice_weight"],cfg["loss"]["bce_weight"])
    scaler=torch.cuda.amp.GradScaler(enabled=tr["mixed_precision"] and device.type=="cuda")
    writer=SummaryWriter(f"runs/{cfg['experiment']['name']}")

    best_iou=0; patience=0
    ckpt_dir=Path(cfg["checkpoints"]["dir"]); final_dir=Path(cfg["checkpoints"]["final_dir"])

    for epoch in range(1,tr["epochs"]+1):
        model.train(); tl=[]
        for t1,t2,masks in TL:
            t1,t2,masks=t1.to(device),t2.to(device),masks.to(device)
            optimizer.zero_grad()
            with torch.cuda.amp.autocast(enabled=tr["mixed_precision"] and device.type=="cuda"):
                loss=criterion(model(t1,t2),masks)
            scaler.scale(loss).backward(); scaler.step(optimizer); scaler.update()
            tl.append(loss.item())
        model.eval(); vl=[]; vi=[]; vf=[]
        with torch.no_grad():
            for t1,t2,masks in VL:
                t1,t2,masks=t1.to(device),t2.to(device),masks.to(device)
                logits=model(t1,t2); vl.append(criterion(logits,masks).item())
                p=(logits[:,1]>0).bool(); vi.append(iou(p,masks)); vf.append(f1(p,masks))
        scheduler.step()
        v_iou=np.mean(vi)
        writer.add_scalars("Loss",{"train":np.mean(tl),"val":np.mean(vl)},epoch)
        writer.add_scalar("Val/IoU",v_iou,epoch); writer.add_scalar("Val/F1",np.mean(vf),epoch)
        logger.info(f"Epoch {epoch:03d} | train={np.mean(tl):.4f} val={np.mean(vl):.4f} IoU={v_iou:.4f}")
        if v_iou>best_iou:
            best_iou=v_iou; patience=0
            best_path=final_dir/"siamese_best.pth"; best_path.parent.mkdir(parents=True,exist_ok=True)
            torch.save({"epoch":epoch,"model":model.state_dict(),"val_iou":v_iou},best_path)
            logger.info(f"  ✅ Best → {best_path} IoU={best_iou:.4f}")
        else:
            patience+=1
            if patience>=tr["patience"]: logger.info(f"Early stop epoch {epoch}"); break
    writer.close(); logger.info(f"Done. Best IoU: {best_iou:.4f}")

if __name__=="__main__":
    logging.basicConfig(level=logging.INFO); train_supervised()
