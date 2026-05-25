# ============================================================
# CADENA DE MARKOV — ESTADO DE ENGAGEMENT DEL CANAL
# Basado en Views por Post (VPP)
# ============================================================

from pathlib import Path
import pandas as pd
import numpy as np
pd.set_option('display.max_rows', None)
# ============================================================
# 1. CARGAR DATASET
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

csv_path = BASE_DIR / "data" / "mensajes_telegram.csv"

msgs = pd.read_csv(csv_path)

# ============================================================
# 2. EXTRAER FECHA
# ============================================================

msgs["fecha"] = msgs["fecha_col"].astype(str).str[:10]

# ============================================================
# 3. AGREGAR MÉTRICAS DIARIAS
# ============================================================

posts_dia = msgs.groupby("fecha").agg(
    n_posts=("message_id", "count"),
    vistas_dia=("views", "sum"),
    forwards_dia=("forwards", "sum")
).reset_index()

# ============================================================
# 4. CALCULAR VIEWS POR POST
# ============================================================

posts_dia["views_por_post"] = (
    posts_dia["vistas_dia"]
    / posts_dia["n_posts"]
)

# ============================================================
# 5. BASELINE GLOBAL
# ============================================================

MEDIA_GLOBAL = posts_dia["views_por_post"].mean()

print("\n================================================")
print("BASELINE GLOBAL DEL CANAL")
print("================================================")

print(f"Views/post promedio global: {MEDIA_GLOBAL:.2f}")

# ============================================================
# 6. DEFINICIÓN DE ESTADOS
#
# Bajo   : < 90% del promedio
# Normal : ±10% del promedio
# Alto   : > 110% del promedio
# ============================================================

LIM_BAJO = 0.9 * MEDIA_GLOBAL
LIM_ALTO = 1.1 * MEDIA_GLOBAL

print(f"\nUmbral Bajo  : < {LIM_BAJO:.2f}")
print(f"Umbral Alto  : > {LIM_ALTO:.2f}")

def clasificar_estado(vpp):

    if vpp < LIM_BAJO:
        return "Bajo"

    elif vpp > LIM_ALTO:
        return "Alto"

    else:
        return "Normal"

posts_dia["estado"] = posts_dia["views_por_post"].apply(
    clasificar_estado
)

# ============================================================
# 7. ORDENAR TEMPORALMENTE
# ============================================================

posts_dia = posts_dia.sort_values("fecha").reset_index(drop=True)

# ============================================================
# 8. MOSTRAR RESUMEN DIARIO
# ============================================================

print("\n================================================")
print("RESUMEN DIARIO")
print("================================================")

print(posts_dia[[
    "fecha",
    "n_posts",
    "vistas_dia",
    "views_por_post",
    "estado"
]].head(200))

# ============================================================
# 9. CONSTRUIR MATRIZ DE TRANSICIONES
# ============================================================

ESTADOS = ["Bajo", "Normal", "Alto"]

conteos = pd.DataFrame(
    0,
    index=ESTADOS,
    columns=ESTADOS
)

secuencia = posts_dia["estado"].tolist()

for i in range(len(secuencia) - 1):

    estado_actual = secuencia[i]
    estado_sig = secuencia[i + 1]

    conteos.loc[estado_actual, estado_sig] += 1

# ============================================================
# 10. NORMALIZAR MATRIZ
# ============================================================

P = conteos.div(conteos.sum(axis=1), axis=0)

print("\n================================================")
print("CONTEOS DE TRANSICIÓN")
print("================================================")

print(conteos)

print("\n================================================")
print("MATRIZ DE TRANSICIÓN")
print("================================================")

print(P.round(4))

# ============================================================
# 11. DISTRIBUCIÓN ESTACIONARIA
# ============================================================

P_np = P.values

n = P_np.shape[0]

A = P_np.T - np.eye(n)
A[-1, :] = 1.0

b = np.zeros(n)
b[-1] = 1.0

pi = np.linalg.solve(A, b)

print("\n================================================")
print("DISTRIBUCIÓN ESTACIONARIA")
print("================================================")

for estado, prob in zip(ESTADOS, pi):
    print(f"{estado}: {prob:.4f}")

# ============================================================
# 12. ESTADÍSTICAS POR ESTADO
# ============================================================

print("\n================================================")
print("ESTADÍSTICAS POR ESTADO")
print("================================================")

stats = posts_dia.groupby("estado").agg(
    dias=("fecha", "count"),
    views_post_promedio=("views_por_post", "mean"),
    vistas_totales=("vistas_dia", "mean"),
    posts_promedio=("n_posts", "mean"),
    forwards_promedio=("forwards_dia", "mean")
)

print(stats.round(2))

# ============================================================
# 13. INTERPRETACIÓN AUTOMÁTICA
# ============================================================

print("\n================================================")
print("INTERPRETACIÓN")
print("================================================")

for i, estado in enumerate(ESTADOS):

    idx_max = np.argmax(P_np[i])

    estado_destino = ESTADOS[idx_max]
    prob_max = P_np[i, idx_max]

    print(
        f"Si el canal está en estado '{estado}', "
        f"la transición más probable es hacia "
        f"'{estado_destino}' "
        f"(p = {prob_max:.3f})"
    )

# ============================================================
# 14. DISTRIBUCIÓN DE ESTADOS
# ============================================================

print("\n================================================")
print("DISTRIBUCIÓN DE ESTADOS")
print("================================================")

print(posts_dia["estado"].value_counts())

# ============================================================
# 15. MATRIZ FINAL FORMATEADA
# ============================================================

print("\n================================================")
print("MATRIZ FINAL")
print("================================================")

print(P.round(3).to_string())
