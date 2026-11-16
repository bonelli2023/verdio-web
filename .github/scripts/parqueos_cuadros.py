"""
🅿️ Corta los parqueos de OpenStreetMap en cuadros de 0.5° (~55 km) para Verdio.
Entrada: archivos .osm.pbf ya filtrados (solo amenity=parking y sus nodos).
Salida: carpeta t/ con un archivo por cuadro "{i}_{j}.csv.gz" (i = floor(lat/0.5), j = floor(lon/0.5)),
        con las mismas columnas que la consulta en vivo de Verdio, y t/index.txt.
"""
import gzip, math, os, sys, time
import osmium

STEP = 0.5
COLS = ["name", "fee", "access", "parking", "maxstay", "operator"]

def clean(v):
    return (v or "").replace("|", "/").replace("\n", " ").replace("\r", " ").strip()

class H(osmium.SimpleHandler):
    def __init__(self, out):
        super().__init__()
        self.out = out
    def add(self, typ, oid, lat, lon, tags):
        if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return
        key = f"{math.floor(lat / STEP)}_{math.floor(lon / STEP)}"
        row = [typ, str(oid), f"{lat:.7f}", f"{lon:.7f}"] + [clean(tags.get(c)) for c in COLS]
        self.out.setdefault(key, {})[(typ, oid)] = "|".join(row)
    def node(self, n):
        if n.tags.get("amenity") == "parking":
            self.add("node", n.id, n.location.lat, n.location.lon, n.tags)
    def way(self, w):
        if w.tags.get("amenity") != "parking":
            return
        pts = [(nd.lat, nd.lon) for nd in w.nodes if nd.location.valid()]
        if not pts:
            return
        if len(pts) > 1 and pts[0] == pts[-1]:
            pts = pts[:-1]
        self.add("way", w.id, sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts), w.tags)

def main():
    outdir = sys.argv[1]
    files = sys.argv[2:]
    tiles = {}
    for f in files:
        t0 = time.time()
        H(tiles).apply_file(f, locations=True)
        print(f"{f}: listo en {time.time()-t0:.0f} s, cuadros hasta ahora {len(tiles)}", flush=True)
    os.makedirs(os.path.join(outdir, "t"), exist_ok=True)
    head = "@type|@id|@lat|@lon|" + "|".join(COLS)
    total = 0
    for key, rows in tiles.items():
        with gzip.open(os.path.join(outdir, "t", key + ".csv.gz"), "wt", encoding="utf-8", compresslevel=9) as g:
            g.write(head + "\n" + "\n".join(rows.values()) + "\n")
        total += len(rows)
    with open(os.path.join(outdir, "t", "index.txt"), "w") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime())} {total} parqueos en {len(tiles)} cuadros de {STEP} grados\n")
    print(open(os.path.join(outdir, "t", "index.txt")).read())

if __name__ == "__main__":
    main()
