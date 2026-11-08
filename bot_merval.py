import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import norm
import requests
import os

# --- CONFIGURACIÓN DE LA APP WEB ---
st.set_page_config(page_title="Bot de Opciones Seguro", page_icon="🛡️", layout="wide")
st.title("🛡️ Monitor de Opciones Automatizado y Seguro")
st.caption("Conexión encriptada en tiempo real a InvertirOnline mediante API REST.")

BASE_URL_IOL = "https://invertironline.com"

# =====================================================================
# 🛠️ CAPA DE SEGURIDAD 1: LOGUEO EN VIVO DESDE LA BARRA LATERAL
# =====================================================================
st.sidebar.header("🔐 Acceso Seguro a IOL")
st.sidebar.markdown("Sus datos se procesan únicamente en la memoria RAM y se destruyen al cerrar la pestaña.")

# Campos con formato 'password' para ocultar las letras con puntitos negros
iol_usuario = st.sidebar.text_input("Usuario / Email IOL:", placeholder="ejemplo@correo.com")
iol_password = st.sidebar.text_input("Contraseña IOL:", type="password", placeholder="******")

st.sidebar.divider()
st.sidebar.header("⚙️ Configuración de Mercado")
activo = st.sidebar.selectbox("Seleccioná el Activo a Operar:", options=["GGAL", "YPF"], index=0)
timeframe = st.sidebar.selectbox("Temporalidad (Timeframe):", options=["15m", "1h", "1d"], index=1)
tasa_caucion = st.sidebar.number_input("Tasa Caución (TNA):", value=0.35, step=0.01)
vol_historica = st.sidebar.number_input("Volatilidad Base (σ):", value=0.48, step=0.01)

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

# =====================================================================
# FUNCIONES DE CONEXIÓN SEGURO CON LA API DE IOL
# =====================================================================
def obtener_token_iol(usuario, contrasenia):
    url = f"{BASE_URL_IOL}/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded", "Host": "://invertironline.com"}
    payload = {"username": usuario, "password": contrasenia, "grant_type": "password"}
    try:
        res = requests.post(url, headers=headers, data=payload)
        if res.status_code == 200:
            return res.json().get("access_token")
        return None
    except:
        return None

def descargar_paneles_opciones_api(token, simbolo):
    url = f"{BASE_URL_IOL}/api/v2/byma/Titulos/{simbolo}/Opciones"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            return pd.DataFrame(res.json())
        return None
    except:
        return None

# =====================================================================
# INTERFAZ Y PROCESAMIENTO CENTRAL
# =====================================================================
precio_spot = 4915.00 if activo == "GGAL" else 6455.00

st.subheader("📋 1. Datos del Activo Subyacente")
col1, col2, col3 = st.columns(3)
col1.metric(f"Precio Acción Spot ({activo})", f"${precio_spot:,.2f} ARS")
col2.metric("Tasa de Caución (r)", f"{tasa_caucion*100:.1f}% TNA")
col3.metric("Volatilidad del Modelo (σ)", f"{vol_historica*100:.1f}%")

st.divider()
st.subheader("📊 2. Lista Integral Traída Automáticamente de IOL")

# El bot solo corre la lógica si el usuario escribió datos en las cajitas de texto de la barra lateral
if iol_usuario and iol_password:
    token_activo = obtener_token_iol(iol_usuario, iol_password)
    
    if token_activo:
        st.success("🟢 Autenticación Segura Exitosa. Cargando matriz de opciones desde IOL en tiempo real...")
        df_opciones_iol = descargar_paneles_opciones_api(token_activo, activo)
        
        if df_opciones_iol is not None and not df_opciones_iol.empty:
            resultados_finales = []
            
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
                cant_c = int(fila.get('cantidadCompra', 0))
                cant_v = int(fila.get('cantidadVenta', 0))
                monto_vol = float(str(fila.get('montoOperado', 0)).replace(',', '.'))
                
                if precio_mkt <= 0: continue
                
                tiempo_vencimiento = 42 / 365.0
                metricas = calcular_black_scholes_y_griegas(precio_spot, strike_k, tiempo_vencimiento, tasa_caucion, vol_historica, tipo_opcion)
                
                resultados_calculados.append({
                    'Símbolo Lote': lote, 'Último Operado': precio_mkt,
                    'Precio Teórico BS': metricas['Precio_Teorico'], 'Delta (Δ)': metricas['Delta'],
                    'Cant Compra': cant_c, 'Precio Compra (Bid)': p_compra,
                    'Precio Venta (Ask)': p_venta, 'Cant Venta': cant_v, 'Monto Operado ($)': monto_vol
                })
                
            df_interactivo = pd.DataFrame(resultados_finales)
            st.dataframe(
                df_interactivo.style.format({
                    'Último Operado': '${:,.2f}', 'Precio Teórico BS': '${:,.2f}',
                    'Precio Compra (Bid)': '${:,.2f}', 'Precio Venta (Ask)': '${:,.2f}',
                    'Delta (Δ)': '{:,.2f}', 'Monto Operado ($)': '${:,.0f}'
                }),
                use_container_width=True, hide_index=True
            )
        else:
            st.warning("⚠️ No se encontraron opciones operables en este momento para el ticker seleccionado.")
    else:
        st.error("❌ Credenciales inválidas. InvertirOnline rechazó el acceso. Revise su usuario y contraseña.")
else:
    st.info("🔑 Por favor, ingrese sus datos de acceso a InvertirOnline en la barra lateral izquierda para activar el escaneo automático.")