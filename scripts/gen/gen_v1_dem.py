"""V1 (HISTORICO): heightmap a partir de dados de elevacao REAIS.

Baixa tiles do Mapzen/AWS Terrain Tiles (formato "terrarium": elevacao
codificada em RGB) da regiao que inspirou o mapa Chernarus do DayZ/Arma --
norte da Boemia, entre Usti nad Labem e Decin, Republica Tcheca (~50.7215,
14.1411), conforme https://longcreek.me/blog/2021/chernarus-irl

Por que virou historico: 774m x 774m de DEM real e pequeno demais para um mapa
de jogo com 4 biomas, e o relevo real da regiao e suave demais para dar
contraste entre biomas. A v2 (gen_v2.py) gera terreno procedural com erosao
hidraulica, que da mais controle. Este script fica como referencia de como
puxar DEM real quando quisermos fidelidade geografica.

Uso:  python3 gen_v1_dem.py
"""
import math
import os

import numpy as np
from PIL import Image

LAT, LON = 50.7215, 14.1411     # referencia real do Chernarus
ZOOM = 15                        # ~3.02 m/pixel nessa latitude
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "..", "Heightmaps")
TILE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/%d/%d/%d.png"


def deg2tile(lat, lon, zoom):
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def fetch_mosaic(lat, lon, zoom):
    """Baixa 3x3 tiles ao redor do ponto e devolve elevacao em metros."""
    import urllib.request
    cx, cy = deg2tile(lat, lon, zoom)
    mosaic = Image.new("RGB", (768, 768))
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            url = TILE_URL % (zoom, cx + dx, cy + dy)
            with urllib.request.urlopen(url, timeout=60) as r:
                tile = Image.open(r).convert("RGB")
            mosaic.paste(tile, ((dx + 1) * 256, (dy + 1) * 256))
    a = np.asarray(mosaic).astype(np.float64)
    # formato terrarium: elevacao = (R*256 + G + B/256) - 32768
    return (a[:, :, 0] * 256 + a[:, :, 1] + a[:, :, 2] / 256) - 32768


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    elev = fetch_mosaic(LAT, LON, ZOOM)

    # recorta 256x256 do centro (~774m x 774m a 3.02 m/px)
    c, half = 384, 128
    crop = elev[c - half:c + half, c - half:c + half]
    print("elevacao real: %.1f a %.1f m" % (crop.min(), crop.max()))

    try:
        from scipy.ndimage import gaussian_filter
        crop = gaussian_filter(crop, sigma=1.8)  # SRTM 30m reamostrado e ruidoso
    except ImportError:
        print("scipy ausente: pulando suavizacao")

    # codifica em R+G, o formato que landscape_import_heightmap_from_render_target
    # espera quando bImportHeightFromRGChannel=True.
    # Com Landscape ScaleZ=100:  H = 32768 + elevacao_m * 128
    baseline = crop.mean()
    h16 = np.clip(32768 + (crop - baseline) * 128.0, 0, 65535).astype(np.uint16)
    rgba = np.stack([(h16 >> 8).astype(np.uint8),
                     (h16 & 0xFF).astype(np.uint8),
                     np.zeros(h16.shape, np.uint8),
                     np.full(h16.shape, 255, np.uint8)], axis=-1)
    out = os.path.join(OUT_DIR, "v1_dem_real_rg_256.png")
    Image.fromarray(rgba, "RGBA").save(out)
    print("salvo:", out)


if __name__ == "__main__":
    main()
