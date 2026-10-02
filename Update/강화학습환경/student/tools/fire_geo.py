# -*- coding: utf-8 -*-
"""사격 기하 (학습 리플레이) — 사격 시 ATA·거리 분포를 두 구간 비교로 그린다. 학습 아님, 측정.

사용:
    python student/tools/fire_geo.py                      # 기본 두 구간
    python student/tools/fire_geo.py 14200 15000 22200 22800 [out.png]

정의(실측으로 고친 것, 2026-09-02):
 - **사격 시점** = 상대 HP 가 감소한 모든 프레임. (개시 프레임만 세면 ATA 0~0.1도가 비고 거리가 914 m 에만 몰린다.)
 - **ATA** = student/my_observation.py `_ata_deg` 와 동일한 NED 공식.
   리플레이 CSV 는 위경도·고도(ENU, z=위)이므로 (rn,re,rd)=(북,동,-위)로 변환해서 넣는다.
   ENU 그대로 pitch 부호를 쓰면 87도가 나온다(부호 뒤집힘).
검증: 값이 맞으면 우리 사격 ATA 중앙 ~1.0도, 거리 중앙 ~914 m(WEZ 상한)로 나온다.
"""
import sys
import json,glob,re,os,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.family']='Malgun Gothic'; plt.rcParams['axes.unicode_minus']=False
R=6371000.0
def collect(lo,hi):
    ata_us=[];dist_us=[];ata_th=[];dist_th=[]
    for f in glob.glob('artifacts/replays/AeroFlyer_final_v2r7/engagement_replays/stage_35_iter_*/episode_*/*_summary.json'):
        it=int(re.search(r'iter_(\d+)',f).group(1))
        if not(lo<=it<hi): continue
        d=os.path.dirname(f)
        po=glob.glob(d+'/*ownship*.csv'); pt=glob.glob(d+'/*target*.csv')
        if not po or not pt: continue
        try:
            o=np.genfromtxt(po[0],delimiter=',',names=True,encoding='utf-8')
            t=np.genfromtxt(pt[0],delimiter=',',names=True,encoding='utf-8')
        except Exception: continue
        n=min(len(o),len(t))
        if n<10: continue
        o=o[:n]; t=t[:n]
        lat0=math.radians(float(o['Latitude'][0]))
        ex=(t['Longitude']-o['Longitude'])*math.cos(lat0)*math.pi/180*R
        ey=(t['Latitude']-o['Latitude'])*math.pi/180*R
        ez=t['Altitude']-o['Altitude']
        dist=np.sqrt(ex**2+ey**2+ez**2)
        # student/my_observation.py _ata_deg 와 동일: NED(rn,re,rd) 기준
        def ata(pitch,yaw,rnn,ree,rdd):
            p=np.radians(pitch); y=np.radians(yaw)
            n=np.sqrt(rnn**2+ree**2+rdd**2)+1e-9
            un,ue,ud=rnn/n,ree/n,rdd/n
            x1=np.cos(y)*un+np.sin(y)*ue
            bx=np.cos(p)*x1-np.sin(p)*ud
            return np.degrees(np.arccos(np.clip(bx,-1,1)))
        # ENU(ex=동, ey=북, ez=위) -> NED(rn=북, re=동, rd=아래)
        r_n, r_e, r_d = ey, ex, -ez
        a_us=ata(o['Pitch_deg'],o['Yaw_deg'],r_n,r_e,r_d)
        a_th=ata(t['Pitch_deg'],t['Yaw_deg'],-r_n,-r_e,-r_d)
        dh_t=np.diff(t['Health']); dh_o=np.diff(o['Health'])
        # 데미지가 들어간 **모든** 프레임 (2026-09-02 정정)
        #   '개시 프레임만' 세면 진입 순간만 잡혀 ATA 0~0.1도가 통째로 비고
        #   거리도 사거리 상한(914 m)에만 몰린다. 실제 사격은 각을 좁히며 이어진다.
        idx_us=np.where(dh_t<-1e-7)[0]
        idx_th=np.where(dh_o<-1e-7)[0]
        ata_us+=list(a_us[idx_us]); dist_us+=list(dist[idx_us])
        ata_th+=list(a_th[idx_th]); dist_th+=list(dist[idx_th])
    return map(np.array,(ata_us,dist_us,ata_th,dist_th))
_a=sys.argv[1:]
if len(_a)>=4:
    bands=[(f'A iter{_a[0]}~{_a[1]}',int(_a[0]),int(_a[1])),(f'B iter{_a[2]}~{_a[3]}',int(_a[2]),int(_a[3]))]
    OUT=_a[4] if len(_a)>4 else 'docs_fire_geo.png'
else:
    bands=[('정점본 iter14200~15000',14200,15000),('최신본 iter22200~22800',22200,22800)]
    OUT='docs_fire_geo.png'
fig,axs=plt.subplots(2,2,figsize=(16,9))
for i,(name,lo,hi) in enumerate(bands):
    au,du,at,dt=collect(lo,hi)
    ax=axs[i][0]
    ax.hist(au,bins=np.arange(0,5.05,0.1),color='tab:blue',alpha=0.85,label=f'우리 사격 n={len(au)}')
    ax.hist(at,bins=np.arange(0,5.05,0.1),color='tab:red',alpha=0.5,label=f'피격(상대 사격) n={len(at)}')
    ax.set_title(f'{name} — 사격 시 ATA 분포 (0~5도, 0.1도 칸)',fontsize=10)
    ax.set_xlabel('ATA(도)'); ax.legend(fontsize=8); ax.tick_params(labelsize=8)
    # 원점 고정: y축 0 과 x축 0 이 떨어져 보이지 않게 (2026-09-02)
    ax.set_xlim(0,5); ax.set_ylim(bottom=0); ax.margins(x=0,y=0)
    bx=axs[i][1]
    bx.hist(du,bins=np.arange(0,1000,25),color='tab:blue',alpha=0.85,label='우리 사격 거리')
    bx.hist(dt,bins=np.arange(0,1000,25),color='tab:red',alpha=0.5,label='피격 거리')
    bx.axvline(914.4,color='k',ls='--',lw=1); bx.axvline(152.4,color='k',ls=':',lw=1)
    med=np.median(du) if len(du) else float('nan')
    bx.set_title(f'{name} — 사격 거리 분포 (25m 칸, 중앙 {med:.0f}m; 점선=WEZ 152/914m)',fontsize=10)
    bx.set_xlabel('거리(m)'); bx.legend(fontsize=8); bx.tick_params(labelsize=8)
    bx.set_xlim(0,1000); bx.set_ylim(bottom=0); bx.margins(x=0,y=0)
    print(f'{name}: 우리 사격 {len(au)}프레임 ATA중앙 {np.median(au):.2f}도 거리중앙 {np.median(du):.0f}m | 피격 {len(at)}프레임 ATA중앙 {np.median(at):.2f}도 거리중앙 {np.median(dt):.0f}m')
fig.suptitle('사격 기하 비교 — 정점본 vs 최신본 (학습 리플레이)',fontsize=13)
fig.tight_layout(rect=[0,0,1,0.96]); fig.savefig(OUT,dpi=110)
print('saved',OUT)
