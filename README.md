# El Promo Hunter — Dataset para Modelado de Embudo de Conversión

Dataset extraído del canal de Telegram **El Promo Hunter** (~5500 suscriptores) para un proyecto universitario de **Modelos y Simulación** (simulación de eventos discretos del embudo: publicación → visualización → clic → compra).

## Descripción del canal

Canal de marketing de afiliados de Amazon en Colombia. Publica ofertas de productos con imagen, calificación, precio original, precio con descuento, cupón y link de afiliado (`amzn.to`).

## Datos extraídos

**Período:** 1 enero 2026 → 23 mayo 2026  
**Total mensajes:** 21,097  
**Total vistas:** 6,613,127  
**Vistas promedio por post:** 313.5

## Estructura del repositorio

```
data/
├── mensajes_telegram.csv      # Dataset principal (21,097 filas, sin texto crudo)
├── mensajes_completos.json    # Igual + texto completo de cada mensaje
├── estadisticas_canal.json    # Estadísticas nativas de Telegram (GetBroadcastStatsRequest)
└── resumen_extraccion.json    # Resumen agregado: vistas por hora, día, categoría

scripts/
├── extractor.py               # Extrae mensajes del canal vía Telethon
└── reparser.py                # Re-parsea el JSON con regex ajustados al formato real
```

## Campos del dataset (`mensajes_telegram.csv`)

| Campo | Descripción |
|---|---|
| `message_id` | ID único del mensaje en Telegram |
| `fecha_utc` | Fecha/hora UTC (ISO 8601) |
| `fecha_col` | Fecha/hora hora Colombia (UTC-5) |
| `hora_col` | Hora en Colombia (0–23) |
| `dia_semana` | Día de semana en español |
| `dia_num` | Día numérico (0=Lunes, 6=Domingo) |
| `views` | Vistas del mensaje |
| `forwards` | Reenvíos del mensaje |
| `tiene_media` | `True` si tiene imagen/video |
| `rating` | Calificación del producto (ej: 4.5) |
| `precio_original` | Precio original en COP |
| `precio_descuento` | Precio con descuento en COP |
| `pct_descuento` | Porcentaje de descuento |
| `tiene_cupon` | `True` si tiene código cupón |
| `codigo_cupon` | Código del cupón (si aplica) |
| `link_amazon` | URL corta `amzn.to` |
| `categoria` | Categoría inferida del producto |
| `es_producto` | `True` si es publicación de producto |

## Resumen estadístico

### Métricas clave
| Métrica | Valor |
|---|---|
| Rating medio | 4.48 / 5.0 |
| Precio descuento medio | $105,407 COP |
| Precio original medio | $164,426 COP |
| % descuento medio | 45.5% |
| Posts con cupón | 9,602 (45.5%) |

### Vistas por categoría
| Categoría | Posts | Vistas/post |
|---|---|---|
| Tecnología | 6,443 | 317.3 |
| Hogar | 3,435 | 312.6 |
| Salud/Belleza | 1,705 | 307.6 |
| Ropa | 1,626 | 310.6 |
| Juguetes | 720 | 312.8 |
| Deportes | 242 | 315.4 |

### Vistas por día de semana
| Día | Vistas promedio |
|---|---|
| Domingo | 340.1 |
| Lunes | 335.8 |
| Martes | 326.7 |
| Miércoles | 308.0 |
| Sábado | 297.9 |
| Viernes | 297.1 |
| Jueves | 296.1 |

### Horas con más vistas (hora Colombia)
Las horas de madrugada (1–3h) acumulan el doble de vistas por post que el horario diurno, aunque concentran muy pocos posts. El horario de mayor volumen es 9h–20h.

## Uso

### Requisitos
```bash
pip install telethon pandas openpyxl
```

### Re-extraer datos frescos
```bash
python scripts/extractor.py
# Pide api_id, api_hash y teléfono — obtenerlos en https://my.telegram.org/apps
```

### Re-parsear sin reconectarse a Telegram
```bash
python scripts/reparser.py
```

## Contexto académico

Este dataset se usa para calibrar distribuciones de probabilidad en un modelo de simulación de eventos discretos del embudo de conversión de un canal de afiliados:

```
Publicación → Visualización → Clic en link → Compra
```

Las variables clave para la simulación son:
- Tasa de llegada de vistas (distribución por hora/día)
- Probabilidad de clic según categoría, descuento y rating
- Efecto del cupón en conversión

## Notas

- Los precios están en **pesos colombianos (COP)**
- El punto (`.`) en los precios es **separador de miles**, no decimal (ej: `$18.773` = 18,773 COP ≈ $4.5 USD)
- Las vistas de Telegram son acumulativas (no por sesión)
- Los datos de clics reales en links de afiliado están en Amazon Associates, no en Telegram
