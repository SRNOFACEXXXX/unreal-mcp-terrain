"""Gerador de terreno v2 - baseado em tecnicas consolidadas da comunidade.

Pipeline (na ordem que importa para realismo):
  1. fbm espectral (power-law noise)          -> base continental
  2. mascaras de bioma com fronteiras organicas (noise-warped voronoi)
  3. modulacao de amplitude/altitude por bioma
  4. EROSAO HIDRAULICA (dandrino/terrain-erosion-3-ways)  <- o que faltava
  5. aplainamento dos sitios de cidade/vilarejo (depois da erosao)
  6. weightmaps por inclinacao + altitude + bioma -> pinta o material

Saidas:
  Heightmaps/v2_height_rg.png     (altura codificada em R+G)
  Heightmaps/v2_w_<layer>.png     (peso 0-255 por camada do material)
  Heightmaps/v2_sites.json        (sitios de cidade/vilarejo + camera)
  previews                        (hillshade colorido + mapa de biomas)
"""
import json
import os

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, distance_transform_edt

OUT_UE = "/home/user/projetogame/MCPTest/Heightmaps"
OUT_PREV = "/tmp/claude-1000/-home-user-projetogame-MCPTest/72157eca-594a-4f1a-89c4-096b241da84c/scratchpad"
os.makedirs(OUT_UE, exist_ok=True)

DIM = 636                 # resolucao do heightmap (bate com o Landscape: 5 comps x 127 quads + 1)
GEN = 848                 # gera maior e recorta o centro -> mata o artefato de
                          # wrap do FFT/np.roll nas bordas
WORLD_M = 1270.0          # tamanho real do terreno em metros (635 quads * 200cm)
CELL_M = WORLD_M / DIM    # ~2m por celula

SEED = 20260814
np.random.seed(SEED)


# --------------------------------------------------------------- utilidades
def normalize(x, bounds=(0.0, 1.0)):
    return np.interp(x, (x.min(), x.max()), bounds)


def fbm(shape, p, lower=-np.inf, upper=np.inf):
    """Ruido espectral power-law (util.py do terrain-erosion-3-ways)."""
    freqs = tuple(np.fft.fftfreq(n, d=1.0 / n) for n in shape)
    freq_radial = np.hypot(*np.meshgrid(*freqs))
    envelope = (np.power(freq_radial, p, where=freq_radial != 0) *
                (freq_radial > lower) * (freq_radial < upper))
    envelope[0][0] = 0.0
    phase_noise = np.exp(2j * np.pi * np.random.rand(*shape))
    return normalize(np.real(np.fft.ifft2(np.fft.fft2(phase_noise) * envelope)))


def simple_gradient(a):
    dx = 0.5 * (np.roll(a, 1, axis=0) - np.roll(a, -1, axis=0))
    dy = 0.5 * (np.roll(a, 1, axis=1) - np.roll(a, -1, axis=1))
    return 1j * dx + dy


def sample(a, offset):
    shape = np.array(a.shape)
    delta = np.array((offset.real, offset.imag))
    coords = np.array(np.meshgrid(*map(range, shape))) - delta
    lower = np.floor(coords).astype(int)
    upper = lower + 1
    frac = coords - lower
    lower %= shape[:, np.newaxis, np.newaxis]
    upper %= shape[:, np.newaxis, np.newaxis]
    lerp = lambda x, y, t: (1.0 - t) * x + t * y
    return lerp(lerp(a[lower[1], lower[0]], a[lower[1], upper[0]], frac[0]),
                lerp(a[upper[1], lower[0]], a[upper[1], upper[0]], frac[0]),
                frac[1])


def displace(a, delta):
    fns = {-1: lambda x: -x, 0: lambda x: 1 - np.abs(x), 1: lambda x: x}
    result = np.zeros_like(a)
    for dx in range(-1, 2):
        wx = np.maximum(fns[dx](delta.real), 0.0)
        for dy in range(-1, 2):
            wy = np.maximum(fns[dy](delta.imag), 0.0)
            result += np.roll(np.roll(wx * wy * a, dy, axis=0), dx, axis=1)
    return result


def apply_slippage(terrain, repose_slope, cell_width):
    """Angulo de repouso: suaviza encostas mais ingremes que o material aguenta."""
    delta = simple_gradient(terrain) / cell_width
    smoothed = gaussian_filter(terrain, sigma=1.5)
    return np.select([np.abs(delta) > repose_slope], [smoothed], terrain)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


# ------------------------------------------------- 1. base + 2. biomas
# Trabalha em GEN x GEN e recorta o centro DIM x DIM no fim da erosao.
shape = (GEN, GEN)
base = fbm(shape, -2.0)                    # continental, suave
detail = fbm(shape, -2.4)                  # detalhe medio

# Fronteiras organicas: deforma as coordenadas com ruido antes do voronoi.
warp_x = (fbm(shape, -2.6) - 0.5) * 0.38
warp_y = (fbm(shape, -2.6) - 0.5) * 0.38
yy, xx = np.mgrid[0:GEN, 0:GEN]
u = xx / (GEN - 1) + warp_x               # eixo Y do mundo
v = yy / (GEN - 1) + warp_y               # eixo X do mundo

# O recorte final pega o centro; converte centros de bioma (normalizados no
# mapa final) para coordenadas normalizadas do espaco de geracao.
CROP_OFF = (GEN - DIM) // 2
to_gen = lambda a: (CROP_OFF + a * (DIM - 1)) / (GEN - 1)

# Centros dos 4 biomas. base/amp ficam em espaco NORMALIZADO 0..1 porque a
# erosao do paper e calibrada para esse espaco (terreno 0..1, mundo 200 un).
# A conversao para metros acontece depois da erosao (RELIEF_M).
BIOMES = [
    # nome,        cu,   cv,   base_n, amp_n, rugosidade
    ("mountain",  0.78, 0.20, 0.80, 0.30, 1.00),
    ("forest",    0.24, 0.28, 0.34, 0.14, 0.75),
    ("plains",    0.22, 0.76, 0.12, 0.05, 0.35),
    ("wetland",   0.76, 0.80, 0.04, 0.03, 0.20),
]
RELIEF_M = 300.0   # altura real correspondente a 1.0 normalizado

# pesos suaves por distancia inversa (fronteiras organicas gracas ao warp)
dists = []
for (_n, cu, cv, _b, _a, _r) in BIOMES:
    d = np.hypot(u - to_gen(cu), v - to_gen(cv))
    dists.append(d)
dists = np.stack(dists)                   # (4, DIM, DIM)
SHARP = 4.0                                # quanto maior, fronteira mais nitida
w = 1.0 / (dists ** SHARP + 1e-6)
w /= w.sum(axis=0, keepdims=True)          # normaliza -> soma 1

w_mountain, w_forest, w_plains, w_wetland = w

base_m = sum(w[i] * BIOMES[i][3] for i in range(4))
amp_m = sum(w[i] * BIOMES[i][4] for i in range(4))
rough = sum(w[i] * BIOMES[i][5] for i in range(4))

# ------------------------------------------------- 3. composicao inicial
# tudo em espaco normalizado 0..1 (requisito da erosao calibrada do paper)
terrain = base_m + amp_m * ((base - 0.5) * 1.4 + (detail - 0.5) * 0.9 * rough)
terrain = gaussian_filter(terrain, sigma=1.0)
terrain = np.clip(terrain, 0.0, 1.2)

print("pre-erosao  normalizado min/max: %.3f / %.3f  (= %.0f a %.0f m)"
      % (terrain.min(), terrain.max(),
         terrain.min() * RELIEF_M, terrain.max() * RELIEF_M))

# ------------------------------------------------- 4. EROSAO HIDRAULICA
# Mesmos parametros/escala do terrain-erosion-3-ways: mundo de 200 unidades.
FULL_WIDTH = 200.0
cell_width = FULL_WIDTH / GEN
cell_area = cell_width ** 2

rain_rate = 0.0008 * cell_area
evaporation_rate = 0.0005
min_height_delta = 0.05
repose_slope = 0.03
gravity = 30.0
sediment_capacity_constant = 50.0
dissolving_rate = 0.25
deposition_rate = 0.001

ITER = 320   # o paper usa 1.4*dim; 320 ja da drenagem clara e roda rapido

sediment = np.zeros_like(terrain)
water = np.zeros_like(terrain)
velocity = np.zeros_like(terrain)

for i in range(ITER):
    water += np.random.rand(*shape) * rain_rate

    gradient = simple_gradient(terrain)
    gradient = np.select([np.abs(gradient) < 1e-10],
                         [np.exp(2j * np.pi * np.random.rand(*shape))],
                         gradient)
    gradient /= np.abs(gradient)

    neighbor_height = sample(terrain, -gradient)
    height_delta = terrain - neighbor_height

    sediment_capacity = ((np.maximum(height_delta, min_height_delta) / cell_width)
                         * velocity * water * sediment_capacity_constant)
    deposited = np.select(
        [height_delta < 0, sediment > sediment_capacity],
        [np.minimum(height_delta, sediment),
         deposition_rate * (sediment - sediment_capacity)],
        dissolving_rate * (sediment - sediment_capacity))
    deposited = np.maximum(-height_delta, deposited)

    sediment -= deposited
    terrain += deposited
    sediment = displace(sediment, gradient)
    water = displace(water, gradient)

    terrain = apply_slippage(terrain, repose_slope, cell_width)
    velocity = gravity * height_delta / cell_width
    water *= 1 - evaporation_rate

    if (i + 1) % 80 == 0:
        print("  erosao %d/%d" % (i + 1, ITER))

print("pos-erosao  normalizado min/max: %.3f / %.3f" % (terrain.min(), terrain.max()))

# acumulacao de agua -> onde correm rios (usada para o material e para o lago)
flow = gaussian_filter(water, sigma=1.5)
flow_n = normalize(flow)

# ---- recorta o centro: remove o artefato de wrap das bordas ----
o = CROP_OFF
terrain = terrain[o:o + DIM, o:o + DIM]
flow_n = flow_n[o:o + DIM, o:o + DIM]
w = w[:, o:o + DIM, o:o + DIM]
w_mountain, w_forest, w_plains, w_wetland = w
shape = (DIM, DIM)

# ---- converte para METROS (a erosao terminou; agora e espaco de mundo) ----
terrain = terrain * RELIEF_M
print("pos-erosao  em metros  min/max: %.1f / %.1f m" % (terrain.min(), terrain.max()))

# ------------------------------------------------- 5. sitios de assentamento
# escolhe pontos planos dentro de cada bioma, longe de encosta forte
gy, gx = np.gradient(terrain, CELL_M)
slope_rad = np.arctan(np.hypot(gx, gy))
slope_deg = np.degrees(slope_rad)
flatness = 1.0 - normalize(gaussian_filter(slope_deg, sigma=3))

SITE_PLAN = [
    ("mountain", 2, 38.0),
    ("forest", 3, 55.0),
    ("plains", 3, 80.0),
    ("wetland", 2, 45.0),
]
BIOME_IDX = {b[0]: i for i, b in enumerate(BIOMES)}
NAMES = {
    "mountain": ["Vila de Montanha", "Posto de Mineracao"],
    "forest": ["Vilarejo da Floresta", "Serraria", "Abrigo de Cacadores"],
    "plains": ["Cidade da Planicie", "Fazenda Coletiva", "Silo Ferroviario"],
    "wetland": ["Vila do Pantano", "Cais de Pesca"],
}

sites = []
occupied = np.zeros(shape, dtype=bool)

for biome, count, radius_m in SITE_PLAN:
    bi = BIOME_IDX[biome]
    score = w[bi] * flatness
    score[occupied] = -1
    # evita bordas do mapa
    margin = int(DIM * 0.08)
    score[:margin, :] = -1
    score[-margin:, :] = -1
    score[:, :margin] = -1
    score[:, -margin:] = -1

    for k in range(count):
        idx = np.argmax(score)
        sy, sx = np.unravel_index(idx, shape)
        if score[sy, sx] <= 0:
            break
        r_px = radius_m / CELL_M
        yy2, xx2 = np.mgrid[0:DIM, 0:DIM]
        d_px = np.hypot(xx2 - sx, yy2 - sy)

        # Aplaina para a MEDIA LOCAL (nao para um plano perfeito): remove as
        # ondulacoes mas preserva a inclinacao geral -> parece clareira/terraco
        # em vez de um disco recortado.
        local_mean = gaussian_filter(terrain, sigma=r_px * 0.85)
        blend_px = r_px * 1.6
        t = smoothstep(r_px * 0.35, r_px + blend_px, d_px)
        terrain = terrain * t + local_mean * (1 - t)
        target = float(terrain[sy, sx])

        # marca ocupado (com folga) para nao colar dois assentamentos
        occupied |= d_px < (r_px * 3.2)
        score[d_px < (r_px * 3.2)] = -1

        name = NAMES[biome][k] if k < len(NAMES[biome]) else "%s %d" % (biome, k)
        sites.append({
            "name": name,
            "biome": biome,
            "px": [int(sx), int(sy)],
            # mundo: X segue as linhas (sy), Y segue as colunas (sx)
            "world_x_cm": float(sy) / (DIM - 1) * WORLD_M * 100.0,
            "world_y_cm": float(sx) / (DIM - 1) * WORLD_M * 100.0,
            "elev_m": target,
            "radius_m": radius_m,
        })

print("sitios criados: %d" % len(sites))
for s in sites:
    print("   %-22s %-9s elev %6.1f m" % (s["name"], s["biome"], s["elev_m"]))

terrain = gaussian_filter(terrain, sigma=0.7)

# guarda o estado para poder re-tunar o material sem repetir a erosao
np.savez_compressed("%s/v2_state.npz" % OUT_PREV, terrain=terrain, flow_n=flow_n,
                    w_mountain=w_mountain, w_forest=w_forest,
                    w_plains=w_plains, w_wetland=w_wetland)

# ------------------------------------------------- 6. weightmaps do material
gy, gx = np.gradient(terrain, CELL_M)
slope_deg = np.degrees(np.arctan(np.hypot(gx, gy)))
elev = terrain

# Rocha: so encosta realmente ingreme ou cume alto (senao o mapa fica marrom)
w_rock = np.clip(smoothstep(30, 50, slope_deg) * 1.0
                 + smoothstep(185, 245, elev) * 0.7, 0, 1)

# Grama: dominante em tudo que nao e rocha e nao e ingreme.
# E o "chao padrao" do mapa -> mantem o terreno verde e legivel.
w_grass = (1 - w_rock) * np.clip(1.35 * (1 - smoothstep(26, 46, slope_deg)), 0, 1)
w_grass *= (0.75 + 0.25 * (w_plains + w_forest + w_wetland))

# Folhas secas: sub-bosque da floresta (bioma floresta, encosta suave)
w_leaves = (1 - w_rock) * w_forest * 1.1 * (1 - smoothstep(20, 38, slope_deg))

# Terra seca: apenas margens de agua e transicao para rocha (nao e mais o padrao)
w_dry = np.clip(flow_n * 0.55 * (1 - w_rock)
                + smoothstep(24, 40, slope_deg) * 0.35 * (1 - w_rock), 0, 1)

# normaliza para somar 1 (o material espera pesos coerentes)
total = w_rock + w_grass + w_leaves + w_dry + 1e-6
w_rock, w_grass, w_leaves, w_dry = (w_rock / total, w_grass / total,
                                    w_leaves / total, w_dry / total)

LAYERS = {
    "Rock_01": w_rock,
    "Grass_Ivy_01": w_grass,
    "Dead_Leaves_01": w_leaves,
    "Dry_Ground_01": w_dry,
}

for name, arr in LAYERS.items():
    a8 = np.clip(arr * 255, 0, 255).astype(np.uint8)
    rgba = np.stack([a8, a8, a8, np.full_like(a8, 255)], axis=-1)
    Image.fromarray(rgba, mode="RGBA").save("%s/v2_w_%s.png" % (OUT_UE, name))
print("weightmaps salvos: %s" % list(LAYERS))

# ------------------------------------------------- codifica altura em R+G
BASELINE_M = 100.0   # WorldZ_cm = (H-32768)/128*ScaleZ ; com ScaleZ=100 -> H = 32768 + elev_m*128
h16 = 32768 + (elev - BASELINE_M) * 128.0
if h16.min() < 0 or h16.max() > 65535:
    print("AVISO: altura fora do range 16 bits, comprimindo")
h16 = np.clip(h16, 0, 65535).astype(np.uint16)
print("h16 min/max: %d / %d  (elev %.1f a %.1f m)" % (h16.min(), h16.max(), elev.min(), elev.max()))

R = (h16 >> 8).astype(np.uint8)
G = (h16 & 0xFF).astype(np.uint8)
rgba = np.stack([R, G, np.zeros_like(R), np.full_like(R, 255)], axis=-1)
Image.fromarray(rgba, mode="RGBA").save("%s/v2_height_rg.png" % OUT_UE)

# ------------------------------------------------- cameras de inspecao
def world_of(px, py, above_m=0.0):
    return {
        "x_cm": float(py) / (DIM - 1) * WORLD_M * 100.0,
        "y_cm": float(px) / (DIM - 1) * WORLD_M * 100.0,
        "z_cm": float(terrain[py, px] + above_m) * 100.0,
    }


cams = []
# uma camera olhando cada bioma a partir de fora, na altura do terreno
cam_defs = [
    ("Montanha", 0.78, 0.20, 45.0),
    ("Floresta", 0.24, 0.28, 30.0),
    ("Planicie", 0.22, 0.76, 25.0),
    ("Pantano", 0.76, 0.80, 20.0),
]
for name, cu, cv, h in cam_defs:
    px, py = int(cu * (DIM - 1)), int(cv * (DIM - 1))
    cams.append({"name": name, "target": world_of(px, py), "eye_height_m": h})

meta = {
    "dim": DIM, "world_m": WORLD_M, "cell_m": CELL_M,
    "scale_z": 100.0, "baseline_m": BASELINE_M,
    "elev_min_m": float(elev.min()), "elev_max_m": float(elev.max()),
    "landscape_origin_cm": [-31700.0, -31700.0],
    "sites": sites, "cameras": cams,
    "layers": list(LAYERS),
}
with open("%s/v2_sites.json" % OUT_UE, "w") as f:
    json.dump(meta, f, indent=2)

# ------------------------------------------------- previews
# hillshade colorido proprio (sem matplotlib): rampa hipsometrica + relevo
stops = [
    (0.00, (56, 84, 68)),      # fundo de vale / umido
    (0.16, (74, 110, 58)),     # planicie verde
    (0.38, (110, 124, 62)),    # colina
    (0.60, (128, 112, 82)),    # encosta
    (0.80, (140, 134, 128)),   # rocha
    (1.00, (238, 240, 244)),   # cume
]
en = normalize(elev)
ramp = np.zeros(elev.shape + (3,), dtype=np.float64)
for (a0, c0), (a1, c1) in zip(stops[:-1], stops[1:]):
    m = (en >= a0) & (en <= a1)
    t = np.zeros_like(en)
    t[m] = (en[m] - a0) / (a1 - a0)
    for ch in range(3):
        ramp[..., ch][m] = c0[ch] + (c1[ch] - c0[ch]) * t[m]

# rocha explicita onde o weightmap diz que e rocha
for ch, c in enumerate((150, 146, 140)):
    ramp[..., ch] = ramp[..., ch] * (1 - w_rock * 0.55) + c * (w_rock * 0.55)

gy2, gx2 = np.gradient(elev, CELL_M)
slope2 = np.arctan(np.hypot(gx2, gy2))
aspect2 = np.arctan2(-gx2, gy2)
az, alt = np.radians(315), np.radians(42)
shade = (np.sin(alt) * np.cos(slope2)
         + np.cos(alt) * np.sin(slope2) * np.cos(az - aspect2))
shade = np.clip(shade, 0, 1)
shade = 0.35 + 0.85 * shade
img = np.clip(ramp * shade[..., None], 0, 255).astype(np.uint8)
Image.fromarray(img, mode="RGB").resize((1000, 1000), Image.LANCZOS).save(
    "%s/v2_preview_terrain.png" % OUT_PREV)

# mapa de biomas + sitios
colors = np.array([(120, 112, 104), (34, 78, 40), (168, 186, 96), (64, 110, 124)])
w_stack = np.stack([w_mountain, w_forest, w_plains, w_wetland], axis=-1)
bio = (w_stack @ colors).astype(np.uint8)
bio_img = Image.fromarray(bio, mode="RGB").resize((1000, 1000), Image.NEAREST)
try:
    from PIL import ImageDraw
    d = ImageDraw.Draw(bio_img)
    for s in sites:
        cx = s["px"][0] / (DIM - 1) * 1000
        cy = s["px"][1] / (DIM - 1) * 1000
        r = 9
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 60, 60), outline=(0, 0, 0))
        d.text((cx + 12, cy - 7), s["name"], fill=(255, 255, 255))
except Exception as e:
    print("anotacao falhou: %r" % (e,))
bio_img.save("%s/v2_preview_biomes.png" % OUT_PREV)

print("OK v2 gerado")
