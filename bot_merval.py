import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import norm
import requests

# --- CONFIGURACIÓN DE LA APP ADAPTADA A MÓVIL ---
st.set_page_config(page_title="Bot Mobile Seguro", page_icon="📱", layout="centered")

st.title("📱 Monitor de Opciones Mobile")
st.caption("Diseño optimizado para pantallas verticales en tiempo real")

BASE_URL_IOL = "https://invertironline.com"

# --- MÓDULO DE ACCESO SEGURO EN EL TOPE ---
with st.expander("🔐 Configurar Cuenta e Indicadores", expanded=True):
    iol_usuario = st.text_input("Usuario / Email IOL:", placeholder="ejemplo@correo.com")
    iol_password = st.text_input("Contraseña IOL:", type="password", placeholder="******")
    
    c1, c2 = st.columns(2)
    activo = c1.selectbox("Activo:", options=["GGAL", "YPF"], index=0)
    timeframe = c2.selectbox("Timeframe:", options=["15m", "1h", "1d"], index=1)
    
    tasa_caucion = st.number_input("Tasa Caución (TNA):", value=0.35, step=0.01)
    vol_historica = st.number_input("Volatilidad Base (σ):", value=0.48, step=0.01)

# =====================================================================
# MOTOR MATEMÁTICO (BLACK-SCHOLES)
# =====================================================================
def calcular_black_scholes_y_griegas(S, K, T, r, sigma, tipo="CALL"):
    if T <= 0:
        return {"Precio_Teorico": max(0, S - K) if tipo == "CALL" else max(0, K - S), "Delta": 1.0 if (tipo=="CALL" and S>K) else -1.0}
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if tipo == "CALL":
        precio = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        delta = norm.cdf(d1)
    else:
        precio = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        delta = norm.cdf(d1) - 1.0
    return {"Precio_Teorico": precio, "Delta": delta}

def obtener_token_iol(usuario, contrasenia):
    url = f"{BASE_URL_IOL}/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded", "Host": "://invertironline.com"}
    payload = {"username": usuario, "password": contrasenia, "grant_type": "password"}
    try:
        res = requests.post(url, headers=headers, data=payload)
        if res.status_code == 200: return res.json().get("access_token")
        return None
    except: return None

def descargar_paneles_opciones_api(token, simbolo):
    url = f"{BASE_URL_IOL}/api/v2/byma/Titulos/{simbolo}/Opciones"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200: return pd.DataFrame(res.json())
        return None
    except: return None

# =====================================================================
# RENDERIZADO EN FORMATO TARJETAS VERTICALES (MOBILE VIEW)
# =====================================================================
precio_spot = 4915.00 if activo == "GGAL" else 6455.00

st.metric(label=f"Precio Spot {activo}", value=f"${precio_spot:,.2f} ARS")
st.divider()

if iol_usuario and iol_password:
    token_activo = obtener_token_iol(iol_usuario, iol_password)
    
    if token_activo:
        df_opciones_iol = descargar_paneles_opciones_api(token_activo, activo)
        
        if df_opciones_iol is not None and not df_opciones_iol.empty:
            st.caption("🟢 Conectado a BYMA - Desplácese hacia abajo para ver los lotes")
            
            for _, fila in df_opciones_iol.iterrows():
                lote = fila.get('simbolo', fila.get('descripcion', ''))
                if not lote: continue
                
                tipo_opcion = 'CALL' if 'C' in lote[3:5] else 'PUT'
                try:
                    numeros = ''.join([c for c in lote if c.isdigit()])
                    strike_k = float(numeros)
                except: continue
                
                precio_mkt = float(str(fila.get('ultimoPrecio', 0)).replace(',', '.'))
                p_compra = float(str(fila.get('precioCompra', 0)).replace(',', '.'))
                p_venta = float(str(fila.get('precioVenta', 0)).replace(',', '.'))
                monto_vol = float(str(fila.get('montoOperado', 0)).replace(',', '.'))
                
                # Omitir lotes sin liquidez en la rueda para no saturar el celular
                if precio_mkt <= 0 or monto_vol < 100000: continue
                
                tiempo_vencimiento = 42 / 365.0
                metricas = calcular_black_scholes_y_griegas(precio_spot, strike_k, tiempo_vencimiento, tasa_caucion, vol_historica, tipo_opcion)
                
                # --- DISEÑO DE TARJETA INDEPENDIENTE POR LOTE ---
                color_icono = "🟢" if tipo_opcion == "CALL" else "🔴"
                with st.container(border=True):
                    st.markdown(f"### {color_icono} {lote} | Strike: ${strike_k:,.0f}")
                    
                    mc1, mc2, mc3 = st.columns(3)
                    mc1.metric("Último Mkt", f"${precio_mkt:.2f}")
                    mc2.metric("Teórico BS", f"${metricas['Precio_Teorico']:.2f}")
                    mc3.metric("Delta (Δ)", f"{metricas['Delta']:.2f}")
                    
                    # Línea de puntas optimizada para pantallas angostas
                    st.markdown(f"**Puntas:** C: ${p_compra:.2f} ─── V: ${p_venta:.2f}")
                    st.caption(f"Volumen Operado: ${monto_vol:,.0f} ARS")
        else:
            st.warning("No se encontraron opciones líquidas en este momento.")
    else:
        st.error("Credenciales inválidas en InvertirOnline.")
else:
    st.info("👋 Ingrese sus datos en el bloque superior para activar el escaneo automático en su pantalla móvil.")
