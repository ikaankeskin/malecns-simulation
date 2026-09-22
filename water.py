"""Toy river, rain and soil moisture; not a hydraulic or biological model."""
import math

CROP_WATER = 0.3
RAIN = (0.0018, 0.0007, 0.0, 0.001)
EVAPORATION = (0.0007, 0.0009, 0.0022, 0.0007)
FLOW = (1.0, 0.8, 0.12, 0.6)


def create(soil, seed):
    half=soil['half'];phase=(seed % 997)*0.017
    def river_x(y):
        return half*(.35*math.sin(3*y/half+phase)+.12*math.sin(7*y/half+phase))
    points=[dict(x=river_x(-half+2*half*i/64),y=-half+2*half*i/64) for i in range(65)]
    banks=[]
    for i in range(soil['n']**2):
        x=-half+(i%soil['n']+.5)*soil['size'];y=-half+(i//soil['n']+.5)*soil['size']
        banks.append(max(0,1-abs(x-river_x(y))/(soil['size']*.75+2)))
    return dict(moisture=[.45+.45*b for b in banks],banks=banks,river=points,
                rain=0.0,river_input=0.0,evaporated=0.0,uptake=0.0,irrigated=0.0,
                reserve=3.0,crop_water=CROP_WATER,flow=1.0,weather='rain')


def advance(soil, tick, rules):
    w=soil.get('water')
    if w is None:return
    season=(tick//rules['season_length'])%4 if rules['seasons'] else 1
    w['flow']=FLOW[season];w['weather']=('rain','light rain','drought','returning rain')[season]
    for i,v in enumerate(w['moisture']):
        rain=min(RAIN[season],1-v);v+=rain;w['rain']+=rain
        river=min(.006*w['banks'][i]*FLOW[season],1-v);v+=river;w['river_input']+=river
        loss=min(EVAPORATION[season],v);v-=loss;w['evaporated']+=loss
        w['moisture'][i]=v
    old=list(w['moisture']);n=soil['n']
    # Pairwise diffusion is conservative and independent of traversal order.
    for i,v in enumerate(old):
        for j in ([i+1] if i%n<n-1 else [])+([i+n] if i+n<len(old) else []):
            flux=.035*(v-old[j]);w['moisture'][i]-=flux;w['moisture'][j]+=flux


def irrigate(soil, index):
    w=soil.get('water') if soil else None
    if w is None or type(index) is not int or not 0<=index<len(w['moisture']):return 0
    amount=min(.25,w['reserve'],max(0,1-w['moisture'][index]))
    w['reserve']-=amount;w['moisture'][index]+=amount;w['irrigated']+=amount
    return amount
