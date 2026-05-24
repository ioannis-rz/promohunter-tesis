"""
Re-parsea mensajes_completos.json con regex ajustados al formato real del canal.
No necesita reconectarse a Telegram.
"""

import json
import re
from pathlib import Path
import pandas as pd

CARPETA = Path("/home/ubuntu/datos_promohunter")

CATEGORIAS = {
    "tecnología":    ["laptop", "computador", "celular", "auricular", "audífono",
                      "tablet", "teclado", "mouse", "ratón", "cámara", "usb",
                      "cable", "cargador", "smartphone", "monitor", "disco",
                      "memoria", "ssd", "alexa", "echo", "fire", "kindle",
                      "smartwatch", "reloj inteligente", "robot aspirador",
                      "impresora", "router", "wifi", "bocina", "parlante",
                      "altavoz", "micrófono", "webcam", "proyector", "drone",
                      "dashcam", "salpicadero", "dashcam", "gopro", "acción"],
    "hogar":         ["silla", "sofá", "almohada", "colchón", "cocina", "olla",
                      "sartén", "licuadora", "aspiradora", "lámpara", "ventilador",
                      "aire acondicionado", "cafetera", "tostadora", "microondas",
                      "organizador", "toalla", "cortina", "mueble", "estante",
                      "encimera", "placa eléctrica", "quemador", "freidora",
                      "hervidor", "purificador", "humidificador", "deshumidificador",
                      "plancha", "vaporizador", "colador", "cuchillo", "tabla de cortar",
                      "contenedor", "recipiente", "termo", "botella", "jarra",
                      "escoba", "trapeador", "limpieza", "lavadora", "secadora"],
    "salud/belleza": ["crema", "shampoo", "champú", "perfume", "vitamina",
                      "suplemento", "mascarilla", "serum", "sérum", "protector solar",
                      "maquillaje", "cepillo", "afeitadora", "depiladora", "báscula",
                      "tensiómetro", "termómetro", "masajeador", "pestañas",
                      "visón", "labial", "base", "corrector", "sombra", "rimmel",
                      "gel", "loción", "aceite esencial", "difusor", "aromaterapia",
                      "limpieza facial", "cera de oído", "limpiador de oído",
                      "blanqueador dental", "hilo dental", "irrigador", "derma"],
    "ropa":          ["camisa", "camiseta", "pantalón", "zapato", "tenis",
                      "zapatilla", "vestido", "chaqueta", "abrigo", "calcetín",
                      "ropa", "bermuda", "falda", "bolso", "cartera", "mochila",
                      "cinturón", "gorra", "sombrero", "guante", "bufanda",
                      "pijama", "ropa interior", "bikini", "bañador", "traje de baño",
                      "bolsa de playa", "maleta", "equipaje"],
    "juguetes":      ["juguete", "lego", "muñeca", "puzzle", "rompecabezas",
                      "figura", "peluche", "juego de mesa", "niño", "niña",
                      "bebé", "infantil", "educativo", "construcción", "bloques"],
    "deportes":      ["pesa", "mancuerna", "bicicleta", "caminadora", "banda elástica",
                      "colchoneta", "yoga", "deporte", "fitness", "piscina",
                      "pelota", "raqueta", "guante de boxeo", "saco de boxeo",
                      "proteína", "creatina", "pre-entreno", "gym", "gimnasio",
                      "correr", "running", "ciclismo", "natación", "escalada"],
}

DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def inferir_categoria(texto: str) -> str:
    if not texto:
        return "otra"
    t = texto.lower()
    for cat, palabras in CATEGORIAS.items():
        if any(p in t for p in palabras):
            return cat
    return "otra"


def parsear_cop(s: str):
    """Convierte '18.773' (miles COP) o '18,773' a float. Retorna None si falla."""
    if not s:
        return None
    try:
        # Formato colombiano: punto como separador de miles
        limpio = s.replace(".", "").replace(",", "")
        return float(limpio)
    except Exception:
        return None


def parsear_mensaje(texto: str) -> dict:
    if not texto:
        return _vacio()

    # ── Rating ────────────────────────────────────────────────────────────
    # Formato: "⭐️ Calificación: 4.2 (2.031)"
    rating = None
    m = re.search(r'[Cc]alificaci[oó]n:\s*(\d+[.,]\d+)', texto)
    if m:
        rating = float(m.group(1).replace(",", "."))

    # ── Precios COP ───────────────────────────────────────────────────────
    # Formato: "💸 Precio: $18.773 COP (original $37.510 COP)"
    precio_descuento = None
    precio_original  = None

    m_precio = re.search(
        r'Precio:\s*\$([\d.,]+)\s*COP.*?original\s*\$([\d.,]+)\s*COP',
        texto, re.IGNORECASE | re.DOTALL
    )
    if m_precio:
        precio_descuento = parsear_cop(m_precio.group(1))
        precio_original  = parsear_cop(m_precio.group(2))
    else:
        # Fallback: solo precio de descuento
        m_solo = re.search(r'Precio:\s*\$([\d.,]+)\s*COP', texto, re.IGNORECASE)
        if m_solo:
            precio_descuento = parsear_cop(m_solo.group(1))

    # ── Porcentaje de descuento ────────────────────────────────────────────
    pct_descuento = None
    m_pct = re.search(r'(\d{1,3})\s*%\s*(?:dto|desc|off|de\s+desc)', texto, re.IGNORECASE)
    if m_pct:
        pct_descuento = float(m_pct.group(1))
    elif precio_original and precio_descuento and precio_original > 0:
        pct_descuento = round((1 - precio_descuento / precio_original) * 100, 1)

    # ── Cupón ─────────────────────────────────────────────────────────────
    # "¡No necesita!" → sin cupón
    # "`CODIGO`"       → con cupón
    no_necesita = bool(re.search(r'no\s+necesita', texto, re.IGNORECASE))

    codigo_cupon = None
    m_cup = re.search(r'[Cc]up[oó]n:\s*`([A-Z0-9]{3,20})`', texto)
    if not m_cup:
        # Variantes sin backtick: Cupón: CODIGO (todo mayúsculas, sin espacios)
        m_cup = re.search(r'[Cc]up[oó]n:\s*([A-Z0-9]{4,20})(?:\s|$)', texto)
    if m_cup and not no_necesita:
        codigo_cupon = m_cup.group(1).upper()

    tiene_cupon = codigo_cupon is not None

    # ── Link Amazon ───────────────────────────────────────────────────────
    link_amazon = None
    # Preferir el link de "Ir a Amazon" sobre el de Prime
    m_link = re.search(r'Ir a Amazon:\s*(https?://\S+)', texto, re.IGNORECASE)
    if not m_link:
        m_link = re.search(r'(https?://(?:amzn\.to|a\.co)/\S+)', texto)
    if m_link:
        link_amazon = m_link.group(1).rstrip(")")

    # ── Es producto ───────────────────────────────────────────────────────
    es_producto = bool(link_amazon or precio_descuento or rating)

    return {
        "rating":           rating,
        "precio_original":  precio_original,
        "precio_descuento": precio_descuento,
        "pct_descuento":    pct_descuento,
        "tiene_cupon":      tiene_cupon,
        "codigo_cupon":     codigo_cupon,
        "link_amazon":      link_amazon,
        "categoria":        inferir_categoria(texto) if es_producto else "n/a",
        "es_producto":      es_producto,
    }


def _vacio() -> dict:
    return {
        "rating": None, "precio_original": None, "precio_descuento": None,
        "pct_descuento": None, "tiene_cupon": False, "codigo_cupon": None,
        "link_amazon": None, "categoria": "n/a", "es_producto": False,
    }


def calcular_resumen(df: pd.DataFrame) -> dict:
    solo_prod = df[df["es_producto"]]
    vistas_hora = (
        df.groupby("hora_col")["views"]
        .agg(["mean", "count"])
        .rename(columns={"mean": "vistas_promedio", "count": "n_posts"})
        .round(1).to_dict(orient="index")
    )
    vistas_dia = (
        df.groupby("dia_semana")["views"]
        .agg(["mean", "count"])
        .rename(columns={"mean": "vistas_promedio", "count": "n_posts"})
        .round(1).to_dict(orient="index")
    )
    vistas_cat = {}
    if not solo_prod.empty:
        vistas_cat = (
            solo_prod.groupby("categoria")["views"]
            .agg(["mean", "count"])
            .rename(columns={"mean": "vistas_promedio", "count": "n_posts"})
            .round(1).to_dict(orient="index")
        )
    return {
        "total_mensajes":          len(df),
        "total_productos":         int(solo_prod.shape[0]),
        "total_vistas":            int(df["views"].sum()),
        "total_forwards":          int(df["forwards"].sum()),
        "vistas_promedio_global":  round(df["views"].mean(), 1),
        "mensajes_con_cupon":      int(df["tiene_cupon"].sum()),
        "mensajes_con_media":      int(df["tiene_media"].sum()),
        "precio_descuento_medio_COP": round(solo_prod["precio_descuento"].mean(), 0)
                                      if not solo_prod.empty and not solo_prod["precio_descuento"].isna().all() else None,
        "precio_original_medio_COP":  round(solo_prod["precio_original"].mean(), 0)
                                      if not solo_prod.empty and not solo_prod["precio_original"].isna().all() else None,
        "pct_descuento_medio":     round(solo_prod["pct_descuento"].mean(), 1)
                                   if not solo_prod.empty and not solo_prod["pct_descuento"].isna().all() else None,
        "rating_medio":            round(solo_prod["rating"].mean(), 2)
                                   if not solo_prod.empty and not solo_prod["rating"].isna().all() else None,
        "vistas_por_hora_col":     vistas_hora,
        "vistas_por_dia_semana":   vistas_dia,
        "vistas_por_categoria":    vistas_cat,
    }


def main():
    print("Cargando mensajes_completos.json…")
    with open(CARPETA / "mensajes_completos.json", encoding="utf-8") as f:
        registros_orig = json.load(f)
    print(f"  {len(registros_orig)} mensajes cargados")

    print("Re-parseando con regex corregidos…")
    registros = []
    for r in registros_orig:
        parsed = parsear_mensaje(r.get("texto", ""))
        nuevo = {k: v for k, v in r.items()
                 if k not in ("rating", "precio_original", "precio_descuento",
                              "pct_descuento", "tiene_cupon", "codigo_cupon",
                              "link_amazon", "categoria", "es_producto")}
        nuevo.update(parsed)
        registros.append(nuevo)

    df = pd.DataFrame(registros)

    # CSV actualizado
    cols_csv = [c for c in df.columns if c != "texto"]
    df[cols_csv].to_csv(CARPETA / "mensajes_telegram.csv", index=False, encoding="utf-8-sig")
    print("  ✓ mensajes_telegram.csv actualizado")

    # JSON completo actualizado
    with open(CARPETA / "mensajes_completos.json", "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False, indent=2, default=str)
    print("  ✓ mensajes_completos.json actualizado")

    # Resumen actualizado
    resumen = calcular_resumen(df)
    with open(CARPETA / "resumen_extraccion.json", "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2, default=str)
    print("  ✓ resumen_extraccion.json actualizado")

    # Verificación en muestra
    solo_prod = df[df["es_producto"]]
    print(f"\n── Verificación ────────────────────────────────")
    print(f"  Productos detectados:     {len(solo_prod)} / {len(df)}")
    print(f"  Con rating:               {solo_prod['rating'].notna().sum()}")
    print(f"  Con precio descuento:     {solo_prod['precio_descuento'].notna().sum()}")
    print(f"  Con precio original:      {solo_prod['precio_original'].notna().sum()}")
    print(f"  Con cupón:                {solo_prod['tiene_cupon'].sum()}")
    print(f"  Con código de cupón:      {solo_prod['codigo_cupon'].notna().sum()}")
    print(f"\n── Resumen ─────────────────────────────────────")
    print(f"  Precio descuento medio:   ${resumen['precio_descuento_medio_COP']:,.0f} COP")
    print(f"  Precio original medio:    ${resumen['precio_original_medio_COP']:,.0f} COP")
    print(f"  % descuento medio:        {resumen['pct_descuento_medio']}%")
    print(f"  Rating medio:             {resumen['rating_medio']}")
    print(f"\n── Categorías ──────────────────────────────────")
    for cat, d in sorted(resumen["vistas_por_categoria"].items(), key=lambda x: -x[1]["n_posts"]):
        print(f"  {cat:<20} {d['n_posts']:>5} posts  {d['vistas_promedio']:>6.1f} vistas/post")
    print(f"\n── Top horas Colombia (vistas promedio) ────────")
    horas = resumen["vistas_por_hora_col"]
    top_horas = sorted(horas.items(), key=lambda x: -x[1]["vistas_promedio"])[:8]
    for h, d in top_horas:
        print(f"  {h:>2}h  {d['vistas_promedio']:>6.1f} vistas  ({d['n_posts']} posts)")
    print(f"\n── Por día de semana ───────────────────────────")
    for dia, d in sorted(resumen["vistas_por_dia_semana"].items(), key=lambda x: -x[1]["vistas_promedio"]):
        print(f"  {dia:<12} {d['vistas_promedio']:>6.1f} vistas  ({d['n_posts']} posts)")

    print("\n✓ Listo.")


if __name__ == "__main__":
    main()
