"""
Extractor de datos del canal Telegram "El Promo Hunter"
Proyecto universitario — Modelos y Simulación (embudo de conversión)

Uso:
    pip install telethon pandas openpyxl
    python extractor.py

Se pedirán api_id, api_hash y teléfono al ejecutar.
Obtén las credenciales en: https://my.telegram.org/apps
"""

import asyncio
import json
import re
import sys
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
from telethon import TelegramClient
from telethon.tl.functions.stats import GetBroadcastStatsRequest
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument

TZ_COL       = timezone(timedelta(hours=-5))
FECHA_INICIO = datetime(2026, 1, 1, tzinfo=timezone.utc)
FECHA_FIN    = datetime(2026, 5, 23, 23, 59, 59, tzinfo=timezone.utc)
CARPETA      = Path("datos_promohunter")

CATEGORIAS = {
    "tecnología":    ["laptop", "computador", "celular", "auricular", "audífono",
                      "tablet", "teclado", "mouse", "cámara", "usb", "cable",
                      "cargador", "smartphone", "monitor", "disco", "memoria",
                      "ssd", "alexa", "kindle", "smartwatch", "reloj inteligente",
                      "robot aspirador", "impresora", "router", "wifi", "bocina",
                      "parlante", "altavoz", "micrófono", "webcam", "proyector",
                      "drone", "dashcam"],
    "hogar":         ["silla", "sofá", "almohada", "colchón", "cocina", "olla",
                      "sartén", "licuadora", "aspiradora", "lámpara", "ventilador",
                      "cafetera", "tostadora", "microondas", "organizador", "toalla",
                      "cortina", "mueble", "estante", "encimera", "placa eléctrica",
                      "freidora", "hervidor", "purificador", "humidificador",
                      "plancha", "colador", "cuchillo", "contenedor", "termo",
                      "botella", "escoba", "trapeador", "limpieza"],
    "salud/belleza": ["crema", "shampoo", "champú", "perfume", "vitamina",
                      "suplemento", "mascarilla", "serum", "sérum", "protector solar",
                      "maquillaje", "cepillo", "afeitadora", "depiladora", "báscula",
                      "tensiómetro", "masajeador", "pestañas", "labial", "gel",
                      "loción", "aceite esencial", "difusor", "limpieza facial",
                      "cera de oído", "blanqueador dental", "irrigador"],
    "ropa":          ["camisa", "camiseta", "pantalón", "zapato", "tenis",
                      "zapatilla", "vestido", "chaqueta", "abrigo", "calcetín",
                      "ropa", "bermuda", "falda", "bolso", "cartera", "mochila",
                      "cinturón", "gorra", "pijama", "bikini", "bolsa de playa",
                      "maleta", "equipaje"],
    "juguetes":      ["juguete", "lego", "muñeca", "puzzle", "rompecabezas",
                      "figura", "peluche", "juego de mesa", "niño", "niña",
                      "bebé", "infantil", "educativo", "bloques"],
    "deportes":      ["pesa", "mancuerna", "bicicleta", "caminadora",
                      "banda elástica", "colchoneta", "yoga", "deporte",
                      "fitness", "pelota", "raqueta", "guante de boxeo",
                      "proteína", "creatina", "gym", "gimnasio", "running"],
}

DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def inferir_categoria(texto):
    t = texto.lower()
    for cat, palabras in CATEGORIAS.items():
        if any(p in t for p in palabras):
            return cat
    return "otra"


def parsear_cop(s):
    try:
        return float(s.replace(".", "").replace(",", ""))
    except Exception:
        return None


def parsear_mensaje(texto):
    if not texto:
        return _vacio()

    rating = None
    m = re.search(r'[Cc]alificaci[oó]n:\s*(\d+[.,]\d+)', texto)
    if m:
        rating = float(m.group(1).replace(",", "."))

    precio_descuento = precio_original = None
    m_precio = re.search(
        r'Precio:\s*\$([\d.,]+)\s*COP.*?original\s*\$([\d.,]+)\s*COP',
        texto, re.IGNORECASE | re.DOTALL
    )
    if m_precio:
        precio_descuento = parsear_cop(m_precio.group(1))
        precio_original  = parsear_cop(m_precio.group(2))
    else:
        m_solo = re.search(r'Precio:\s*\$([\d.,]+)\s*COP', texto, re.IGNORECASE)
        if m_solo:
            precio_descuento = parsear_cop(m_solo.group(1))

    pct_descuento = None
    m_pct = re.search(r'(\d{1,3})\s*%\s*(?:dto|desc|off|de\s+desc)', texto, re.IGNORECASE)
    if m_pct:
        pct_descuento = float(m_pct.group(1))
    elif precio_original and precio_descuento and precio_original > 0:
        pct_descuento = round((1 - precio_descuento / precio_original) * 100, 1)

    no_necesita = bool(re.search(r'no\s+necesita', texto, re.IGNORECASE))
    codigo_cupon = None
    m_cup = re.search(r'[Cc]up[oó]n:\s*`([A-Z0-9]{3,20})`', texto)
    if not m_cup:
        m_cup = re.search(r'[Cc]up[oó]n:\s*([A-Z0-9]{4,20})(?:\s|$)', texto)
    if m_cup and not no_necesita:
        codigo_cupon = m_cup.group(1).upper()
    tiene_cupon = codigo_cupon is not None

    link_amazon = None
    m_link = re.search(r'Ir a Amazon:\s*(https?://\S+)', texto, re.IGNORECASE)
    if not m_link:
        m_link = re.search(r'(https?://(?:amzn\.to|a\.co)/\S+)', texto)
    if m_link:
        link_amazon = m_link.group(1).rstrip(")")

    es_producto = bool(link_amazon or precio_descuento or rating)

    return {
        "rating": rating, "precio_original": precio_original,
        "precio_descuento": precio_descuento, "pct_descuento": pct_descuento,
        "tiene_cupon": tiene_cupon, "codigo_cupon": codigo_cupon,
        "link_amazon": link_amazon,
        "categoria": inferir_categoria(texto) if es_producto else "n/a",
        "es_producto": es_producto,
    }


def _vacio():
    return {"rating": None, "precio_original": None, "precio_descuento": None,
            "pct_descuento": None, "tiene_cupon": False, "codigo_cupon": None,
            "link_amazon": None, "categoria": "n/a", "es_producto": False}


async def main():
    api_id   = int(input("api_id: ").strip())
    api_hash = input("api_hash: ").strip()
    telefono = input("Teléfono (+57...): ").strip()
    canal    = input("Username del canal (sin @): ").strip()

    client = TelegramClient("sesion_promohunter", api_id, api_hash)
    await client.start(phone=telefono)
    print("Conectado ✓")

    entidad = await client.get_entity(canal)
    print(f"Canal: {getattr(entidad, 'title', canal)} ✓")

    registros = []
    total = 0
    async for msg in client.iter_messages(entidad, reverse=True, offset_date=FECHA_INICIO):
        if msg.date > FECHA_FIN:
            break
        total += 1
        fecha_utc = msg.date
        fecha_col = fecha_utc.astimezone(TZ_COL)
        texto = msg.text or msg.message or ""
        parsed = parsear_mensaje(texto)
        registros.append({
            "message_id": msg.id,
            "fecha_utc": fecha_utc.isoformat(),
            "fecha_col": fecha_col.isoformat(),
            "hora_col": fecha_col.hour,
            "dia_semana": DIAS_ES[fecha_col.weekday()],
            "dia_num": fecha_col.weekday(),
            "views": msg.views or 0,
            "forwards": msg.forwards or 0,
            "tiene_media": isinstance(msg.media, (MessageMediaPhoto, MessageMediaDocument)),
            **parsed,
            "texto": texto,
        })
        if total % 200 == 0:
            print(f"… {total} mensajes ({fecha_col.date()})")

    stats_canal = {}
    try:
        stats = await client(GetBroadcastStatsRequest(channel=entidad, dark=False))
        stats_canal = json.loads(stats.to_json())
    except Exception as e:
        stats_canal = {"error": str(e)}

    await client.disconnect()

    CARPETA.mkdir(exist_ok=True)
    df = pd.DataFrame(registros)
    df[[c for c in df.columns if c != "texto"]].to_csv(
        CARPETA / "mensajes_telegram.csv", index=False, encoding="utf-8-sig")
    with open(CARPETA / "mensajes_completos.json", "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False, indent=2, default=str)
    with open(CARPETA / "estadisticas_canal.json", "w", encoding="utf-8") as f:
        json.dump(stats_canal, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n✓ {len(registros)} mensajes extraídos → datos_promohunter/")


if __name__ == "__main__":
    asyncio.run(main())
