/* Cuentas Claras — la app (una sola página, sin dependencias). */
'use strict';

// ------------------------------------------------------------------ catálogos
const CATS = {
  casa: { n: 'Casa', i: '🏠', c: '--c1' }, super: { n: 'Alimentos', i: '🛒', c: '--c2' }, servicios: { n: 'Servicios', i: '💡', c: '--c3' },
  chicos: { n: 'Hijos y colegio', i: '🎒', c: '--c4' }, salud: { n: 'Salud', i: '🩺', c: '--c5' }, personal: { n: 'Cuidado personal', i: '💇', c: '--c6' },
  transporte: { n: 'Transporte', i: '🚗', c: '--c7' }, salidas: { n: 'Salidas y regalos', i: '🎁', c: '--c8' }, otros: { n: 'Otros', i: '📦', c: '--c0' }
};
const CATS_AHORRO = { ahorro: { n: 'Ahorro', i: '🐷', c: '--c7' }, inversion: { n: 'Inversión', i: '📈', c: '--c3' } };
const SUG_FIJOS = [
  { n: 'Alquiler', c: 'casa', i: '🔑' }, { n: 'Expensas', c: 'casa', i: '🏢' }, { n: 'Luz', c: 'servicios', i: '💡' }, { n: 'Gas', c: 'servicios', i: '🔥' },
  { n: 'Agua', c: 'servicios', i: '🚰' }, { n: 'ABL / Impuesto municipal', c: 'casa', i: '🏛️' }, { n: 'Prepaga u obra social', c: 'salud', i: '🩺' },
  { n: 'Colegio de los chicos', c: 'chicos', i: '🎒' }, { n: 'Actividades de los chicos', c: 'chicos', i: '⚽' }, { n: 'Teléfono e internet', c: 'servicios', i: '📞' },
  { n: 'Celular', c: 'servicios', i: '📱' }, { n: 'Cable o streaming', c: 'servicios', i: '📺' }, { n: 'Nafta', c: 'transporte', i: '⛽' },
  { n: 'Seguro del auto', c: 'transporte', i: '🚗' }, { n: 'Cuota del auto', c: 'transporte', i: '🚘' }, { n: 'Patente', c: 'transporte', i: '🚙' },
  { n: 'Seguro de hogar', c: 'casa', i: '🛡️' }, { n: 'Ayuda en casa', c: 'casa', i: '🧹' }, { n: 'Clases o gimnasio', c: 'personal', i: '🧘' },
  { n: 'Peluquería', c: 'personal', i: '💇' }, { n: 'Remedios del mes', c: 'salud', i: '💊' }, { n: 'Cuota de la tarjeta', c: 'otros', i: '💳' }
];
const SUG_ING = [
  { n: 'Sueldo', i: '💼' }, { n: 'Trabajo por mi cuenta', i: '💻' }, { n: 'Alquiler que cobro', i: '🔑' },
  { n: 'Cuota alimentaria', i: '🧸' }, { n: 'Extras o changas', i: '✨' }
];
const MESES = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'];
const DIAS = ['domingo','lunes','martes','miércoles','jueves','viernes','sábado'];

// ------------------------------------------------------------------ utilidades
const $ = s => document.querySelector(s);
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const plata = n => '$ ' + Math.round(n || 0).toLocaleString('es-AR');
const corto = n => n >= 1e6 ? '$ ' + (n / 1e6).toLocaleString('es-AR', { maximumFractionDigits: 1 }) + ' M' : '$ ' + Math.round(n / 1e3).toLocaleString('es-AR') + ' mil';
const mayus = s => s.charAt(0).toUpperCase() + s.slice(1);
const colorCat = k => 'var(' + ((CATS[k] || CATS_AHORRO[k] || {}).c || '--c0') + ')';
const icoDe = (nombre, cat) => (SUG_FIJOS.find(s => s.n === nombre) || SUG_ING.find(s => s.n === nombre) || CATS[cat] || CATS_AHORRO[cat] || { i: '💰' }).i;
const pad = n => String(n).padStart(2, '0');
const fechaCorta = iso => iso ? iso.slice(8, 10) + '/' + iso.slice(5, 7) + '/' + iso.slice(0, 4) : '';
const mesNombre = key => MESES[+key.slice(5, 7) - 1];
const leerMonto = v => Number(String(v || '').replace(/\D/g, ''));
const leerPct = v => Math.max(0, parseFloat(String(v || '').replace(',', '.')) || 0);
const mesMas = (key, n) => { const m = +key.slice(5, 7) - 1 + n, y = +key.slice(0, 4) + Math.floor(m / 12); return y + '-' + pad((m % 12 + 12) % 12 + 1); };
const precioFinal = (p, desc, int) => Math.round(p * (1 - desc / 100) * (1 + int / 100) * 100) / 100;
const fmtMonto = n => n ? Math.round(n).toLocaleString('es-AR') : '';
const guardarLocal = (k, v) => { try { localStorage.setItem('cc-' + k, JSON.stringify(v)); } catch (e) {} };
const leerLocal = (k, d) => { try { const v = localStorage.getItem('cc-' + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } };

const esIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
const esAndroid = /Android/i.test(navigator.userAgent);
const instalada = () => matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
const pushSoportado = () => 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
let instalarAndroid = null;
window.addEventListener('beforeinstallprompt', e => { e.preventDefault(); instalarAndroid = e; });

const S = { me: null, unread: 0, vapid: null, pushDevices: 0, demo: false, hoy: null, movMes: null, movTipo: '' };

async function api(method, path, data) {
  const r = await fetch(path, { method, credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'X-CC': '1' }, body: data ? JSON.stringify(data) : undefined });
  let j = {};
  try { j = await r.json(); } catch (e) {}
  if (r.status === 401 && !/\/api\/(login|me)$/.test(path)) { S.me = null; ruta(); throw new Error(j.error || 'Iniciá sesión para seguir'); }
  if (r.status === 402) { hojaPaywall(); throw new Error(j.error || 'Tu prueba terminó'); }
  if (!r.ok) throw new Error(j.error || 'Algo salió mal. Probá de nuevo.');
  return j;
}

let toastT;
function toast(txt) {
  const t = $('#toast');
  t.textContent = txt; t.hidden = false;
  clearTimeout(toastT); toastT = setTimeout(() => { t.hidden = true; }, 2600);
}

function hoyDate() { return S.hoy ? new Date(S.hoy + 'T12:00:00') : new Date(); }
function nombreFecha(iso) {
  if (iso === S.hoy) return 'Hoy';
  const d = new Date(iso + 'T12:00:00'), ay = hoyDate(); ay.setDate(ay.getDate() - 1);
  if (d.toDateString() === ay.toDateString()) return 'Ayer';
  return mayus(DIAS[d.getDay()] + ' ' + d.getDate() + ' de ' + MESES[d.getMonth()]);
}

// ------------------------------------------------------------------ «anotá rápido»: entender lo que escriben
const PALABRAS = {
  super: ['super', 'súper', 'supermercado', 'mercado', 'verdu', 'verduleria', 'verdulería', 'carni', 'carniceria', 'carnicería', 'almacen', 'almacén', 'panaderia', 'panadería', 'pan', 'chino', 'feria', 'comida', 'delivery', 'pedidos', 'fiambre', 'fruta', 'dietetica', 'dietética', 'pollo'],
  transporte: ['nafta', 'combustible', 'colectivo', 'bondi', 'sube', 'uber', 'cabify', 'didi', 'remis', 'remís', 'taxi', 'estacionamiento', 'peaje', 'tren', 'subte', 'auto', 'mecanico', 'mecánico', 'gomeria', 'gomería'],
  salud: ['farmacia', 'remedio', 'remedios', 'medico', 'médico', 'dentista', 'odontologo', 'odontólogo', 'analisis', 'análisis', 'kinesiologo', 'kinesiólogo', 'psicologo', 'psicóloga', 'psicologa', 'anteojos', 'optica', 'óptica'],
  salidas: ['cafe', 'café', 'cena', 'almuerzo', 'cine', 'teatro', 'regalo', 'cumple', 'cumpleaños', 'salida', 'bar', 'helado', 'restaurant', 'restaurante', 'pizza', 'birra', 'vacaciones', 'viaje'],
  personal: ['pelu', 'peluqueria', 'peluquería', 'manicura', 'uñas', 'ropa', 'zapatillas', 'zapatos', 'gimnasio', 'gym', 'yoga', 'pilates', 'cosmetica', 'cosmética', 'perfume', 'depilacion', 'depilación'],
  chicos: ['colegio', 'escuela', 'utiles', 'útiles', 'chicos', 'nene', 'nena', 'hijos', 'juguete', 'jardin', 'jardín', 'cuota colegio', 'uniforme', 'excursion', 'excursión'],
  casa: ['ferreteria', 'ferretería', 'limpieza', 'mueble', 'arreglo', 'plomero', 'electricista', 'pintura', 'bazar', 'alquiler', 'expensas', 'heladera', 'lavarropas', 'microondas', 'cocina', 'colchon', 'colchón', 'electro', 'tele', 'televisor'],
  servicios: ['luz', 'gas', 'agua', 'internet', 'celular', 'cable', 'netflix', 'spotify', 'telefono', 'teléfono', 'recarga']
};

function interpretar(texto) {
  let t = ' ' + texto.replace(/\$/g, ' ') + ' ';
  let monto = 0;
  const m = t.match(/(\d+(?:[.,]\d+)*)\s*(mil|k|lucas?|palos?|millon(?:es)?|millón|m)?(?=\s)/i);
  if (m) {
    let n = m[1];
    // «45.000» o «1.250.000» (puntos de miles) / «1,5» (coma decimal)
    if (/^\d{1,3}(\.\d{3})+$/.test(n)) n = n.replace(/\./g, '');
    n = parseFloat(n.replace(',', '.')) || 0;
    const mult = !m[2] ? 1 : /^(mil|k|luca)/i.test(m[2]) ? 1000 : 1000000;
    monto = Math.round(n * mult);
    t = t.replace(m[0], ' ');
  }
  // la categoría se busca en minúsculas; la descripción queda como la escribieron («Sofi»)
  const low = t.toLowerCase();
  let cat = null;
  for (const [k, palabras] of Object.entries(PALABRAS)) {
    if (palabras.some(p => new RegExp('(^|\\s)' + p.replace(/\s/g, '\\s') + '(\\s|$)').test(low))) { cat = k; break; }
  }
  const descr = t.replace(/\s+/g, ' ').trim().replace(/^(en|de|el|la|los|las)\s+/i, '');
  return { monto, cat, descr: descr ? mayus(descr) : '' };
}

// ------------------------------------------------------------------ íconos
const IC = {
  logo: '<svg viewBox="0 0 36 36" aria-hidden="true"><rect width="36" height="36" rx="10" fill="var(--brand)"/><path d="M10 18.5l5.2 5.2L26.5 12" fill="none" stroke="var(--brand-ink)" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  inicio: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z"/></svg>',
  fijos: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="17" rx="2"/><path d="M3 9h18M8 2v4M16 2v4M8 14l2.5 2.5L16 13"/></svg>',
  cargar: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M12 7v10M7 12h10"/></svg>',
  movs: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 2h14v20l-3-2-2 2-2-2-2 2-2-2-3 2z"/><path d="M9 7h6M9 11h6M9 15h4"/></svg>',
  ingresos: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="6" width="20" height="13" rx="2"/><circle cx="12" cy="12.5" r="2.8"/><path d="M6 10v5M18 10v5"/></svg>',
  campana: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>',
  ajustes: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/></svg>',
  logros: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="9" r="6"/><path d="M8.5 14.5L7 22l5-3 5 3-1.5-7.5"/></svg>',
  tarjeta: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20M6 15h4"/></svg>',
  admin: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 2l8 4v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6z"/></svg>',
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
  compartir: '<svg viewBox="0 0 24 24" fill="none" stroke="#0a84ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-label="botón Compartir"><path d="M12 3v12M8 7l4-4 4 4"/><path d="M5 11v9a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-9"/></svg>'
};

// ------------------------------------------------------------------ armazón
function shell() {
  if ($('#main')) return;
  const extra = (S.me.role === 'admin' ? '<a class="tab" href="#admin" data-vista="admin">' + IC.admin + 'Administración</a>' : '') +
    '<a class="tab" href="#tarjetas" data-vista="tarjetas">' + IC.tarjeta + 'Tarjetas</a><a class="tab" href="#logros" data-vista="logros">' + IC.logros + 'Logros</a><a class="tab" href="#ajustes" data-vista="ajustes">' + IC.ajustes + 'Mi cuenta</a>';
  $('#app').innerHTML =
    '<nav class="nav" aria-label="Secciones">' +
      '<a class="brand" href="#inicio">' + IC.logo + 'Cuentas Claras</a>' +
      '<a class="tab" href="#inicio" data-vista="inicio">' + IC.inicio + 'Inicio</a>' +
      '<a class="tab" href="#fijos" data-vista="fijos">' + IC.fijos + 'Fijos</a>' +
      '<button class="tab cargar" data-acc="cargar">' + IC.cargar + 'Cargar</button>' +
      '<a class="tab" href="#movimientos" data-vista="movimientos">' + IC.movs + 'Egresos</a>' +
      '<a class="tab" href="#ingresos" data-vista="ingresos">' + IC.ingresos + 'Ingresos</a>' +
      '<button class="tab mas" data-acc="mas" aria-label="Más secciones"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><circle cx="5" cy="12" r="1.3"/><circle cx="12" cy="12" r="1.3"/><circle cx="19" cy="12" r="1.3"/></svg>Más</button>' +
      '<div class="nav-extra">' + extra + '</div>' +
    '</nav><main id="main" tabindex="-1"></main>';
}

function cabecera(titulo, sub, racha) {
  const r = racha != null ? racha : (S.racha || 0);
  return '<div class="top"><a class="brand" href="#inicio" aria-label="Cuentas Claras">' + IC.logo + '<span class="brand-txt">Cuentas Claras</span></a><div class="top-acc">' +
    (r > 0 ? '<a class="racha-chip" href="#logros" aria-label="Racha de ' + r + ' días seguidos">🔥 ' + r + '</a>' : '') +
    '<a class="icon-btn" href="#avisos" aria-label="Avisos">' + IC.campana + (S.unread ? '<span class="badge">' + S.unread + '</span>' : '') + '</a>' +
    '<a class="icon-btn" href="#ajustes" aria-label="Mi cuenta">' + IC.ajustes + '</a></div></div>' +
    bannerCuenta() +
    (titulo ? '<div class="saludo"><h1>' + titulo + '</h1>' + (sub ? '<p>' + sub + '</p>' : '') + '</div>' : '');
}

function bannerCuenta() {
  if (S.me.demo) return '<div class="aviso verde"><p><b>Estás viendo un ejemplo.</b> Los datos son de una persona ficticia.</p><button class="btn" data-acc="crear-cuenta">Crear mi cuenta</button></div>';
  const c = S.me.cuenta;
  if (c.estado === 'vencida') return '<div class="aviso rojo"><p><b>Tu acceso está en pausa.</b> Tus datos siguen guardados; suscribite para volver a cargar.</p><a class="btn" href="#cuenta">Suscribirme</a></div>';
  if (c.estado === 'prueba' && c.dias <= 5) return '<div class="aviso"><p><b>' + (c.dias === 1 ? 'Hoy es el último día' : 'Te quedan ' + c.dias + ' días') + ' de prueba gratis.</b> Suscribite para no cortar.</p><a class="btn sec" href="#cuenta">Ver planes</a></div>';
  return '';
}

function marcarNav(v) {
  document.querySelectorAll('.tab[data-vista]').forEach(a => a.dataset.vista === v ? a.setAttribute('aria-current', 'page') : a.removeAttribute('aria-current'));
}

// ------------------------------------------------------------------ rutas
const VISTAS = {};
let vistaActual = null;

async function cargarMe() {
  const r = await api('GET', '/api/me');
  S.me = r.user; S.demo = r.demo; S.mail = r.mail;
  if (r.user) { S.unread = r.unread; S.vapid = r.vapid; S.pushDevices = r.push_devices; S.hoy = r.hoy; }
  document.documentElement.classList.toggle('grande', !!(S.me && S.me.grande));
}

async function ruta() {
  const h = decodeURIComponent(location.hash.slice(1)) || 'inicio';
  cerrarHoja();
  if (h.startsWith('reset/')) return vistaReset(h.slice(6));
  if (!S.me) return vistaBienvenida(h);
  if (!S.me.onboarded && !S.me.demo && S.me.role !== 'admin') return onboarding();
  if (h === 'cargar' || h === 'cargar-ahorro') {
    history.replaceState(null, '', '#inicio');
    await mostrar('inicio');
    return hojaMov(h === 'cargar' ? 'egreso' : 'ahorro');
  }
  await mostrar(VISTAS[h] ? h : 'inicio');
}

async function mostrar(v) {
  shell();
  marcarNav(v);
  const main = $('#main');
  if (vistaActual !== v) { main.innerHTML = '<p class="muted centro" style="padding:40px 0">Cargando…</p>'; window.scrollTo(0, 0); }
  vistaActual = v;
  try {
    const out = await VISTAS[v]();
    if (vistaActual !== v) return;
    main.innerHTML = typeof out === 'string' ? out : out.html;
    $('#tip').hidden = true;
    if (out.despues) out.despues();
  } catch (e) {
    main.innerHTML = cabecera('') + '<div class="bloque vacio"><p>' + esc(e.message) + '</p><button class="btn" data-acc="recargar">Probar de nuevo</button></div>';
  }
}
const refrescar = () => vistaActual ? mostrar(vistaActual) : ruta();

// ------------------------------------------------------------------ bienvenida, ingreso y registro
function pantallaAuth(html) {
  vistaActual = null;
  $('#app').innerHTML = '<div class="auth"><div class="auth-caja">' + html + '</div></div>';
}

function vistaBienvenida(h) {
  if (h === 'entrar') return pantallaAuth(
    '<a class="brand" href="#">' + IC.logo + 'Cuentas Claras</a>' +
    '<form class="bloque" data-form="login" novalidate><h2>Entrar a mi cuenta</h2>' +
      '<div class="campo"><label for="l-mail">Mail</label><input id="l-mail" type="email" autocomplete="email" inputmode="email" required></div>' +
      '<div class="campo"><label for="l-pass">Contraseña</label><input id="l-pass" type="password" autocomplete="current-password" required></div>' +
      '<p class="error" hidden></p><button class="btn ancho" type="submit">Entrar</button>' +
      '<a class="link centro" href="#olvide">Me olvidé la contraseña</a></form>' +
    '<p class="centro">¿No tenés cuenta? <a href="#registro">Creala gratis</a></p>');
  if (h === 'registro') return pantallaAuth(
    '<a class="brand" href="#">' + IC.logo + 'Cuentas Claras</a>' +
    '<form class="bloque" data-form="registro" novalidate><h2>Crear mi cuenta</h2><p class="muted">14 días gratis con todo incluido. No te pedimos tarjeta.</p>' +
      '<div class="campo"><label for="r-nombre">Tu nombre</label><input id="r-nombre" autocomplete="given-name" required></div>' +
      '<div class="campo"><label for="r-mail">Mail</label><input id="r-mail" type="email" autocomplete="email" inputmode="email" required></div>' +
      '<div class="campo"><label for="r-pass">Contraseña <span class="muted">(mínimo 8 caracteres)</span></label><input id="r-pass" type="password" autocomplete="new-password" minlength="8" required></div>' +
      '<label class="casilla"><input id="r-terminos" type="checkbox"><span>Acepto los <button type="button" class="link" data-acc="terminos">términos y la política de privacidad</button>.</span></label>' +
      '<p class="error" hidden></p><button class="btn ancho" type="submit">Crear cuenta</button></form>' +
    '<p class="centro">¿Ya tenés cuenta? <a href="#entrar">Entrá acá</a></p>');
  if (h === 'olvide') return pantallaAuth(
    '<a class="brand" href="#">' + IC.logo + 'Cuentas Claras</a>' +
    '<form class="bloque" data-form="olvide" novalidate><h2>Recuperar la contraseña</h2><p class="muted">Te mandamos un link a tu mail para elegir una nueva.</p>' +
      '<div class="campo"><label for="o-mail">Mail</label><input id="o-mail" type="email" autocomplete="email" inputmode="email" required></div>' +
      '<p class="error" hidden></p><button class="btn ancho" type="submit">Mandarme el link</button></form>' +
    '<p class="centro"><a href="#entrar">Volver</a></p>');
  return pantallaAuth(
    '<a class="brand" href="#">' + IC.logo + 'Cuentas Claras</a>' +
    '<section class="hero"><h1>Tus cuentas, claras.</h1><p style="font-size:1.1rem">Registrá tus ingresos y egresos, controlá tus gastos fijos y tarjetas, y mirá cómo viene el mes de un vistazo.</p></section>' +
    '<div class="puntos">' +
      '<div><span class="ico" style="--k:var(--c2)">🧾</span><span>Cargás un gasto en segundos</span></div>' +
      '<div><span class="ico" style="--k:var(--c1)">📅</span><span>Te avisa antes de cada vencimiento</span></div>' +
      '<div><span class="ico" style="--k:var(--c3)">📊</span><span>Gráficos simples de tu mes</span></div>' +
      '<div><span class="ico" style="--k:var(--c4)">🏅</span><span>Logros por ahorrar y ser constante</span></div></div>' +
    '<a class="btn ancho xl" href="#registro">Probar 14 días gratis</a>' +
    '<a class="btn sec ancho" href="#entrar">Ya tengo cuenta</a>' +
    (S.demo ? '<button class="link centro" data-acc="demo">Ver un ejemplo sin registrarme</button>' : ''));
}

function vistaReset(token) {
  pantallaAuth('<a class="brand" href="#">' + IC.logo + 'Cuentas Claras</a>' +
    '<form class="bloque" data-form="reset" data-token="' + esc(token) + '" novalidate><h2>Elegí una contraseña nueva</h2>' +
    '<div class="campo"><label for="n-pass">Contraseña nueva <span class="muted">(mínimo 8 caracteres)</span></label><input id="n-pass" type="password" autocomplete="new-password" required></div>' +
    '<p class="error" hidden></p><button class="btn ancho" type="submit">Guardar y entrar</button></form>');
}

const FORMS = {
  async login(f) {
    await api('POST', '/api/login', { email: f.querySelector('#l-mail').value, password: f.querySelector('#l-pass').value });
    await cargarMe(); location.hash = '#inicio'; ruta();
  },
  async registro(f) {
    await api('POST', '/api/register', { name: f.querySelector('#r-nombre').value, email: f.querySelector('#r-mail').value,
      password: f.querySelector('#r-pass').value, accept_terms: f.querySelector('#r-terminos').checked });
    await cargarMe(); location.hash = '#inicio'; ruta();
  },
  async olvide(f) {
    const r = await api('POST', '/api/password/forgot', { email: f.querySelector('#o-mail').value });
    f.innerHTML = '<h2>Revisá tu mail</h2><p>Si hay una cuenta con ese mail, te llegó un link para elegir una contraseña nueva. Mirá también en «Spam».</p>' +
      (r.dev_link ? '<p class="chico muted">Modo prueba: <a href="' + esc(r.dev_link) + '">abrir el link</a></p>' : '') +
      (!r.mail ? '<p class="chico muted">Si no te llega, escribile a quien te pasó la app y te genera el link.</p>' : '');
  },
  async reset(f) {
    await api('POST', '/api/password/reset', { token: f.dataset.token, password: f.querySelector('#n-pass').value });
    await cargarMe(); location.hash = '#inicio'; ruta(); toast('Contraseña cambiada');
  }
};

// ------------------------------------------------------------------ primeros pasos
async function onboarding() {
  vistaActual = null;
  const paso = leerLocal('ob-paso', 0);
  const r = await api('GET', '/api/resumen');
  const pasos = '<div class="pasos">' + [0, 1, 2, 3].map(i => '<span class="' + (i <= paso ? 'ok' : '') + '"></span>').join('') + '</div>';
  let html;
  if (paso === 0) {
    const sugs = SUG_ING.filter(s => !r.ingresos.some(x => x.nombre === s.n));
    html = '<h1>¡Hola, ' + esc(S.me.name) + '! Empecemos por tus ingresos</h1><p class="muted">¿Qué ingresos tenés todos los meses? Tocá los que correspondan.</p>' +
      (r.ingresos.length ? '<div class="bloque"><div class="lista">' + r.ingresos.map(x => filaIngreso(x, false)).join('') + '</div></div>' : '') +
      '<div class="sugs">' + sugs.map(s => '<button class="sug" data-acc="sug-ing" data-n="' + esc(s.n) + '"><span aria-hidden="true">' + s.i + '</span>' + esc(s.n) + '</button>').join('') +
      '<button class="sug" data-acc="nuevo-ingreso">+ Otro</button></div>';
  } else if (paso === 1) {
    const sugs = SUG_FIJOS.filter(s => !r.fijos.some(x => x.nombre === s.n));
    html = '<h1>Ahora, tus gastos fijos</h1><p class="muted">Lo que pagás todos los meses. Te vamos a avisar antes de cada vencimiento.</p>' +
      (r.fijos.length ? '<div class="bloque"><div class="lista">' + r.fijos.map(f => filaFijo(f, false)).join('') + '</div></div>' : '') +
      '<div class="sugs">' + sugs.map(s => '<button class="sug" data-acc="sug-fijo" data-n="' + esc(s.n) + '"><span aria-hidden="true">' + s.i + '</span>' + esc(s.n) + '</button>').join('') +
      '<button class="sug" data-acc="nuevo-fijo">+ Otro</button></div>';
  } else if (paso === 2) {
    html = '<h1>Recordatorios</h1><p class="muted">Te avisamos si un día no anotaste nada, cuando se acerca un vencimiento y cuando cierra el mes.</p>' +
      '<div class="bloque"><div class="campo"><label for="ob-hora">¿A qué hora te recordamos anotar los gastos del día?</label>' + selectHora('ob-hora', S.me.notify_hour) + '</div>' +
      bloqueNotif() + '</div>';
  } else {
    html = '<h1>Tenela a mano</h1><p class="muted">Instalala en tu celular: queda como una app más, con su ícono.</p><div class="bloque">' + guiaInstalar() + '</div>';
  }
  pantallaAuth('<a class="brand" href="#">' + IC.logo + 'Cuentas Claras</a>' + pasos + html +
    '<div class="acciones">' + (paso > 0 ? '<button class="btn sec" data-acc="ob-atras">Atrás</button>' : '') +
    '<button class="btn" data-acc="ob-sig">' + (paso === 3 ? 'Empezar a usarla' : 'Siguiente') + '</button></div>' +
    (paso < 3 ? '<button class="link centro" data-acc="ob-fin">Saltear y hacerlo después</button>' : ''));
}

async function obAvanzar(delta) {
  const paso = leerLocal('ob-paso', 0);
  if (paso === 2 && delta > 0 && $('#ob-hora')) await api('PUT', '/api/me', { notify_hour: +$('#ob-hora').value });
  if (paso + delta > 3) return obTerminar();
  guardarLocal('ob-paso', Math.max(0, paso + delta));
  onboarding();
}
async function obTerminar() {
  await api('PUT', '/api/me', { onboarded: true });
  guardarLocal('ob-paso', 0);
  S.me.onboarded = 1;
  location.hash = '#inicio';
  ruta();
}

// ------------------------------------------------------------------ inicio
function filaFijo(f, conCheck = true) {
  let estado;
  if (f.pagado) estado = '<span class="chip good">Pagado' + (f.pagado_monto !== f.monto ? ' ' + plata(f.pagado_monto) : '') + '</span>';
  else if (f.vencido) estado = '<span class="chip bad">Venció el día ' + f.vence + '</span>';
  else {
    const n = f.vence - hoyDate().getDate();
    estado = n === 0 ? '<span class="chip sun">Vence hoy</span>' : n <= 7 ? '<span class="chip sun">Vence en ' + n + (n === 1 ? ' día' : ' días') + '</span>' : '<small>Vence el día ' + f.vence + '</small>';
  }
  return '<div class="fila ' + (f.pagado ? 'pagado' : '') + '">' +
    '<div class="ico" aria-hidden="true" style="--k:' + colorCat(f.cat) + '">' + icoDe(f.nombre, f.cat) + '</div>' +
    '<button class="fila-txt" data-acc="editar-fijo" data-id="' + f.id + '"><b>' + esc(f.nombre) + '</b>' + (conCheck ? estado : '<small>Vence el día ' + f.dia + '</small>') + '</button>' +
    '<span class="fila-monto num">' + plata(f.pagado ? f.pagado_monto : f.monto) + '</span>' +
    (conCheck ? '<button class="check" data-acc="pagar" data-id="' + f.id + '" aria-pressed="' + f.pagado + '" aria-label="' + (f.pagado ? 'Desmarcar pago de ' : 'Marcar como pagado: ') + esc(f.nombre) + '">' + IC.check + '</button>' : '') +
    '</div>';
}

function estadoTarjeta(t) {
  if (t.pagado) return '<span class="chip good">Pagada' + (t.pagado_monto !== t.a_pagar ? ' ' + plata(t.pagado_monto) : '') + '</span>';
  if (t.a_pagar <= 0) return '<small>Sin cuotas este mes</small>';
  if (t.vencido) return '<span class="chip bad">Venció el día ' + t.vence_dia + '</span>';
  const n = t.vence_dia - hoyDate().getDate();
  return n === 0 ? '<span class="chip sun">Vence hoy</span>' : n <= 7 ? '<span class="chip sun">Vence en ' + n + (n === 1 ? ' día' : ' días') + '</span>' : '<small>Vence el día ' + t.vence_dia + '</small>';
}

function filaTarjeta(t) {
  return '<div class="fila ' + (t.pagado ? 'pagado' : '') + '"><div class="ico" aria-hidden="true" style="--k:var(--c4)">💳</div>' +
    '<a class="fila-txt" href="#tarjetas" style="text-decoration:none;color:inherit"><b>Tarjeta ' + esc(t.nombre) + '</b>' + estadoTarjeta(t) + '</a>' +
    '<span class="fila-monto num">' + plata(t.total) + '</span>' +
    (t.a_pagar > 0 || t.pagado ? '<button class="check" data-acc="pagar-tarjeta" data-id="' + t.id + '" aria-pressed="' + t.pagado + '" aria-label="' + (t.pagado ? 'Desmarcar pago de ' : 'Marcar como pagada: ') + esc(t.nombre) + '">' + IC.check + '</button>' : '') + '</div>';
}

function filaIngreso(x, conCheck = true) {
  const estado = x.cobrado ? '<span class="chip good">Cobrado' + (x.cobrado_monto !== x.monto ? ' ' + plata(x.cobrado_monto) : '') + '</span>' : '<small>Se cobra el día ' + x.dia + '</small>';
  return '<div class="fila"><div class="ico" aria-hidden="true" style="--k:var(--c3)">' + icoDe(x.nombre) + '</div>' +
    '<button class="fila-txt" data-acc="editar-ingreso" data-id="' + x.id + '"><b>' + esc(x.nombre) + '</b>' + (conCheck ? estado : '<small>Se cobra el día ' + x.dia + '</small>') + '</button>' +
    '<span class="fila-monto num in">' + plata(x.cobrado ? x.cobrado_monto : x.monto) + '</span>' +
    (conCheck ? '<button class="check" data-acc="cobrar" data-id="' + x.id + '" aria-pressed="' + !!x.cobrado + '" aria-label="' + (x.cobrado ? 'Desmarcar cobro de ' : 'Marcar como cobrado: ') + esc(x.nombre) + '">' + IC.check + '</button>' : '') + '</div>';
}

function detallePago(m) {
  const partes = [];
  if (m.tarjeta_id) {
    const t = (S.tarjetas || []).find(x => x.id === m.tarjeta_id);
    partes.push('💳 ' + esc(t ? t.nombre : 'Tarjeta') + (m.cuotas > 1 ? ' · ' + m.cuotas + ' cuotas de ' + plata(m.monto / m.cuotas) : ''));
  }
  if (m.descuento) partes.push('−' + m.descuento + '%');
  if (m.interes) partes.push('+' + m.interes + '% interés');
  return partes.join(' · ');
}

function filaMov(m) {
  const cat = m.tipo === 'ahorro' ? CATS_AHORRO[m.cat] : m.tipo === 'ingreso' ? { n: 'Ingreso extra', i: '✨' } : CATS[m.cat] || CATS.otros;
  const clase = m.tipo === 'ingreso' ? 'in' : m.tipo === 'ahorro' ? 'ah' : '';
  const det = detallePago(m);
  return '<div class="fila"><div class="ico" aria-hidden="true" style="--k:' + (m.tipo === 'ingreso' ? 'var(--c3)' : colorCat(m.cat)) + '">' + cat.i + '</div>' +
    '<button class="fila-txt" data-acc="editar-mov" data-id="' + m.id + '"><b>' + esc(m.descr || cat.n) + '</b><small>' + cat.n + '</small>' + (det ? '<small>' + det + '</small>' : '') + '</button>' +
    '<span class="fila-monto num ' + clase + '">' + (m.tipo === 'ingreso' ? '+ ' : '') + plata(m.monto) + '</span></div>';
}

function consejos(r) {
  const t = r.totales, out = [];
  const vencidos = r.fijos.filter(f => f.vencido);
  if (vencidos.length) out.push({ t: 'alerta', i: '⏰', h: vencidos.length === 1 ? 'Tenés un pago vencido' : 'Tenés ' + vencidos.length + ' pagos vencidos',
    p: vencidos.map(f => esc(f.nombre)).join(', ') + '. Si ya lo pagaste, tocá el círculo para marcarlo.', b: ['Ver gastos fijos', 'fijos'] });
  if (t.ing > 0) {
    const pct = Math.round(t.fij / t.ing * 100);
    if (pct > 75) out.push({ t: 'alerta', i: '📌', h: 'Los gastos fijos representan el ' + pct + '% de tus ingresos', p: 'Queda poco margen para los egresos variables. Conviene revisar si hay algún servicio o suscripción que ya no uses.' });
    else if (pct > 50) out.push({ t: 'ojo', i: '📌', h: 'Los gastos fijos representan el ' + pct + '% de tus ingresos', p: 'Es una proporción alta. Conviene revisar una vez por año la prepaga, el cable y el celular: suele haber planes más económicos.' });
    else out.push({ t: 'bien', i: '👏', h: 'Los gastos fijos representan el ' + pct + '% de tus ingresos', p: 'Es una proporción saludable y deja margen para los egresos variables.' });
  }
  if (t.ing > 0 && t.saldo < 0) out.push({ t: 'alerta', i: '⚠️', h: 'Este mes los egresos superan a los ingresos', p: 'El saldo es negativo en ' + plata(-t.saldo) + '. Revisá en qué categoría se concentra el gasto.' });
  else if (t.ing > 0 && t.saldo > t.ing * 0.08 && !t.ahorro) out.push({ t: 'bien', i: '🫙', h: 'Este mes tendrías saldo a favor', p: 'Si apartás una parte apenas cobrás, en una cuenta separada, vas armando un fondo para imprevistos.', b: ['Registrar un ahorro', 'ahorro'] });
  if (r.categorias.length) {
    const top = r.categorias.find(([k]) => !['casa', 'servicios', 'salud', 'chicos'].includes(k));
    if (top && t.var > 0 && top[1] > t.ing * 0.15) out.push({ t: '', i: CATS[top[0]] ? CATS[top[0]].i : '🔎', h: 'Donde más se va: ' + (CATS[top[0]] || CATS.otros).n, p: 'Este mes llevás ' + plata(top[1]) + '. Mirar esta categoría es lo que más rápido ayuda a ajustar.' });
  }
  const prox = r.compromisos && r.compromisos[1];
  if (prox && t.ing > 0 && prox.total > t.ing * 0.2) out.push({ t: 'ojo', i: '💳', h: 'En ' + mesNombre(prox.mes) + ' ya tenés ' + plata(prox.total) + ' en cuotas',
    p: 'Es el ' + Math.round(prox.total / t.ing * 100) + '% de tus ingresos. Antes de sumar otra compra en cuotas, conviene mirar la pantalla de Tarjetas.', b: ['Ver tarjetas', 'tarjetas'] });
  const faltan = ['Luz', 'Gas', 'Agua', 'ABL / Impuesto municipal', 'Celular', 'Teléfono e internet'].filter(n => !r.fijos.some(f => f.nombre === n));
  if (faltan.length && r.fijos.length) out.push({ t: '', i: '🤔', h: '¿Falta algún gasto fijo?', p: 'No figuran en tu lista: ' + faltan.slice(0, 3).join(', ') + '. Si corresponde, agregalos para que el balance sea exacto.', b: ['Ver sugerencias', 'fijos'] });
  return out;
}

VISTAS.inicio = async () => {
  const [r, frec] = await Promise.all([api('GET', '/api/resumen'), api('GET', '/api/frecuentes').catch(() => ({ items: [] }))]);
  S.frecuentes = frec.items;
  S.racha = r.racha.dias; S.hoy = r.hoy;
  const t = r.totales, neg = t.saldo < 0;
  if (!r.ingresos.length && !r.fijos.length && t.var === 0) {
    return cabecera('Hola, ' + esc(S.me.name)) + '<div class="bloque vacio"><div class="ico">🌱</div><h2>Primeros pasos</h2><p class="muted">Cargá tus ingresos mensuales y tus gastos fijos. Con eso ya vas a ver el balance del mes.</p>' +
      '<a class="btn" href="#ingresos">Cargar ingresos</a><a class="btn sec" href="#fijos">Cargar gastos fijos</a></div>';
  }
  const base = Math.max(t.ing, t.fij + t.var + t.tarjeta + t.ahorro) || 1;
  const w = x => (Math.max(0, x) / base * 100).toFixed(1) + '%';
  const segs = [[t.fij, 'var(--c1)'], [t.var, 'var(--c2)'], [t.tarjeta, 'var(--c4)'], [t.ahorro, 'var(--c7)'], [t.saldo, 'var(--c3)']].filter(([v]) => v > 0);
  const proximos = r.fijos.filter(f => !f.pagado).slice(0, 4);
  const tarjPend = r.tarjetas.filter(x => !x.pagado && x.a_pagar > 0);
  const proxMes = r.compromisos[1] ? r.compromisos[1].total : 0;
  const d = hoyDate();
  const html = cabecera('Hola, ' + esc(S.me.name), mayus(DIAS[d.getDay()] + ' ' + d.getDate() + ' de ' + MESES[d.getMonth()]), r.racha.dias) +
    bannerInstalar() +
    '<section class="hero ' + (neg ? 'rojo' : '') + '"><span class="eti">' + (neg ? 'Saldo negativo del mes' : 'Saldo disponible del mes') + '</span>' +
      '<span class="grande-num num">' + plata(Math.abs(t.saldo)) + '</span>' +
      (neg ? '<span class="por-dia">Los egresos superan a los ingresos. Revisá el detalle más abajo.</span>'
        : '<span class="por-dia">Equivale a <b class="num">' + plata(r.por_dia) + '</b> por día hasta el ' + r.dias_mes + ' de ' + r.mes_nombre + '.</span>') + '</section>' +
    '<form class="rapido" data-form="rapido"><label for="rapido" class="lab">✍️ Anotá rápido</label><div class="rapido-fila">' +
      '<input id="rapido" autocomplete="off" enterkeyhint="go" placeholder="Ej.: súper 45 mil"><button class="btn" type="submit">Anotar</button></div>' +
      (S.frecuentes.length ? '<div class="frecuentes" aria-label="Tus gastos frecuentes">' + S.frecuentes.map((f, i) =>
        '<button type="button" class="sug" data-acc="frecuente" data-i="' + i + '"><span aria-hidden="true">' + (CATS[f.cat] || CATS.otros).i + '</span>' + esc(f.descr) + ' <span class="muted">' + plata(f.monto) + '</span></button>').join('') + '</div>' : '') +
    '</form>' +
    '<button class="btn ancho xl" data-acc="cargar">+ Cargar un egreso</button>' +
    '<div class="acciones-rap">' +
      (r.racha.hoy_ok ? '<a class="rap" href="#logros"><span>🔥</span>Hoy ya anotaste</a>' : '<button class="rap" data-acc="checkin"><span>🙌</span>Hoy no gasté</button>') +
      '<button class="rap" data-acc="cargar-ahorro"><span>🐷</span>Ahorro</button>' +
      '<button class="rap" data-acc="cargar-ingreso"><span>✨</span>Ingreso extra</button></div>' +
    '<section class="bloque"><h2>Resumen del mes</h2>' +
      '<div class="barra" role="img" aria-label="Gastos fijos ' + plata(t.fij) + ', egresos variables ' + plata(t.var) + ', ahorro ' + plata(t.ahorro) + ', saldo ' + plata(Math.max(0, t.saldo)) + '">' +
        segs.map(([v, c]) => '<span style="width:' + w(v) + ';background:' + c + '"></span>').join('') + '</div>' +
      '<div class="leyenda">' +
        '<div><span class="muted">Ingresos</span><b class="num">' + plata(t.ing) + '</b></div>' +
        '<div><span class="muted"><i class="punto" style="background:var(--c1)"></i>Gastos fijos</span><b class="num">' + plata(t.fij) + '</b></div>' +
        '<div><span class="muted"><i class="punto" style="background:var(--c2)"></i>Egresos variables</span><b class="num">' + plata(t.var) + '</b></div>' +
        (t.tarjeta ? '<div><span class="muted"><i class="punto" style="background:var(--c4)"></i>Tarjetas</span><b class="num">' + plata(t.tarjeta) + '</b></div>' : '') +
        (t.ahorro ? '<div><span class="muted"><i class="punto" style="background:var(--c7)"></i>Ahorro</span><b class="num">' + plata(t.ahorro) + '</b></div>' : '') +
        '<div><span class="muted"><i class="punto" style="background:var(--c3)"></i>Saldo</span><b class="num">' + plata(Math.max(0, t.saldo)) + '</b></div>' +
      '</div>' + bloqueMeta(r) + '</section>' +
    (proximos.length || tarjPend.length ? '<section class="bloque"><div class="bloque-cab"><h2>Próximos vencimientos</h2><a class="link" href="#fijos">Ver todos</a></div><div class="lista">' +
      tarjPend.map(filaTarjeta).join('') + proximos.map(f => filaFijo(f)).join('') + '</div></section>'
      : r.fijos.length ? '<section class="consejo bien"><div class="ico">✅</div><div><h3>Gastos fijos al día</h3><p>No hay vencimientos pendientes este mes.</p></div></section>' : '') +
    (r.tarjetas.length ? '<a class="bloque" href="#tarjetas" style="text-decoration:none;color:inherit"><div class="racha-grande"><span class="fuego">💳</span><div><h3>Tarjetas: ' + plata(t.tarjeta) + ' este mes</h3><p class="muted">' +
      (proxMes ? 'En ' + mesNombre(r.compromisos[1].mes) + ' ya tenés ' + plata(proxMes) + ' en cuotas.' : 'No tenés cuotas para el mes que viene.') + '</p></div></div></a>' : '') +
    (r.categorias.length ? '<section class="bloque"><h2>Egresos por categoría</h2>' + dona(r.categorias) + '</section>' : '') +
    '<section class="bloque"><h2>Ingresos y egresos por mes</h2>' +
      '<div class="ley-meses"><span><i class="punto" style="background:var(--c3)"></i>Ingresos</span><span><i class="punto" style="background:var(--c2)"></i>Egresos</span></div>' +
      '<div id="graf-meses" class="graf" role="img" aria-label="Ingresos y egresos de los últimos meses"></div>' +
      '<p class="muted chico">Tocá cada mes para ver el detalle.' + (r.historial.length < 2 ? ' Cada mes nuevo se suma al gráfico.' : '') + '</p></section>' +
    '<a class="bloque" href="#logros" style="text-decoration:none;color:inherit"><div class="racha-grande"><span class="fuego">🏅</span><div><h3>Tus logros: ' + r.logros.ganados + ' de ' + r.logros.total + '</h3><p class="muted">' +
      (r.racha.dias > 1 ? 'Llevás ' + r.racha.dias + ' días seguidos anotando. ¡Seguí así!' : 'Anotá todos los días para armar tu racha.') + '</p></div></div></a>' +
    '<section class="bloque"><h2>Sugerencias</h2><div class="consejos">' + consejos(r).map(k =>
      '<div class="consejo ' + k.t + '"><div class="ico" aria-hidden="true">' + k.i + '</div><div><h3>' + k.h + '</h3><p>' + k.p + '</p>' +
      (k.b ? (k.b[1] === 'ahorro' ? '<button class="link" data-acc="cargar-ahorro">' + k.b[0] + '</button>' : '<a class="link" href="#' + k.b[1] + '">' + k.b[0] + '</a>') : '') + '</div></div>').join('') + '</div></section>';
  return { html, despues: () => {
    S.historial = r.historial; grafMeses();
    S.tarjetas = r.tarjetas;
    const nuevos = r.logros.sin_ver.length ? r.logros.sin_ver : r.logros_nuevos;
    if (nuevos.length) { festejar(nuevos); api('POST', '/api/logros/vistos').catch(() => {}); }
  } };
};

function bloqueMeta(r) {
  if (!r.meta_ahorro) return '<p class="chico muted">¿Querés ponerte una meta de ahorro por mes? <a href="#ajustes">Definila acá</a>.</p>';
  const pct = Math.min(100, Math.round(r.totales.ahorro / r.meta_ahorro * 100));
  return '<div><p><b>Meta de ahorro:</b> ' + plata(r.totales.ahorro) + ' de ' + plata(r.meta_ahorro) + ' (' + pct + '%)</p>' +
    '<div class="progreso" style="margin-top:8px"><span style="width:' + pct + '%;background:var(--c7)"></span></div></div>';
}

function bannerInstalar() {
  if (instalada() || leerLocal('sin-banner-instalar', false) || S.me.demo) return '';
  return '<div class="aviso verde"><p><b>Instalá la app en tu celular</b> para abrirla con un toque y recibir los recordatorios.</p>' +
    '<div class="acciones" style="flex:0 0 auto"><button class="btn" data-acc="instalar">Cómo instalarla</button><button class="link" data-acc="no-instalar">Ahora no</button></div></div>';
}

// ------------------------------------------------------------------ gráficos
function dona(cats) {
  const total = cats.reduce((a, [, v]) => a + v, 0) || 1;
  const segs = cats.slice(0, 5).map(([k, v]) => ({ n: (CATS[k] || CATS.otros).n, i: (CATS[k] || CATS.otros).i, v, col: colorCat(k) }));
  const resto = cats.slice(5).reduce((a, [, v]) => a + v, 0);
  if (resto) segs.push({ n: 'Resto', i: '📦', v: resto, col: 'var(--c0)' });
  const R = 80, C = 2 * Math.PI * R, gap = segs.length > 1 ? 3 : 0;
  let acc = 0;
  const arcos = segs.map(s => {
    const len = s.v / total * C, vis = Math.max(0.5, len - gap), pct = Math.round(s.v / total * 100);
    const a = '<circle class="arco" cx="100" cy="100" r="' + R + '" fill="none" stroke="' + s.col + '" stroke-width="30" stroke-dasharray="' + vis.toFixed(2) + ' ' + (C - vis).toFixed(2) +
      '" stroke-dashoffset="' + (-acc).toFixed(2) + '" data-tip="' + esc(s.n + '|' + plata(s.v) + ' (' + pct + '%)') + '"></circle>';
    acc += len;
    return a;
  }).join('');
  return '<div class="dona-wrap"><div class="dona"><svg viewBox="0 0 200 200" role="img" aria-label="Egresos por categoría"><g transform="rotate(-90 100 100)">' + arcos + '</g>' +
    '<text x="100" y="94" text-anchor="middle" style="font: 400 12px var(--f-body); fill: var(--muted)">Total del mes</text>' +
    '<text x="100" y="118" text-anchor="middle" style="font: 700 17px var(--f-display); fill: var(--ink)">' + plata(total) + '</text></svg></div>' +
    '<ul class="ley-dona">' + segs.map(s => '<li><i class="punto" style="background:' + s.col + '"></i><span>' + s.i + ' ' + esc(s.n) + '</span><span class="pct">' + Math.round(s.v / total * 100) + '%</span><small class="num">' + plata(s.v) + '</small></li>').join('') + '</ul></div>';
}

function anillo(n, total) {
  const R = 36, C = 2 * Math.PI * R, len = total ? n / total * C : 0;
  return '<svg width="92" height="92" viewBox="0 0 92 92" aria-hidden="true" style="flex:none"><circle cx="46" cy="46" r="' + R + '" fill="none" stroke="var(--line)" stroke-width="10"></circle>' +
    (len ? '<circle cx="46" cy="46" r="' + R + '" fill="none" stroke="var(--good)" stroke-width="10" stroke-linecap="round" stroke-dasharray="' + len.toFixed(2) + ' ' + C.toFixed(2) + '" transform="rotate(-90 46 46)"></circle>' : '') +
    '<text x="46" y="52" text-anchor="middle" style="font: 700 18px var(--f-display); fill: var(--ink)">' + Math.round(total ? n / total * 100 : 0) + '%</text></svg>';
}

function pasoLindo(raw) {
  const p = Math.pow(10, Math.floor(Math.log10(raw))), f = raw / p;
  return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * p;
}
function columna(x, yTop, w, yBase, fill) {
  const h = yBase - yTop;
  if (h <= 0) return '';
  const r = Math.min(4, h, w / 2);
  return '<path fill="' + fill + '" d="M' + x + ',' + yBase + 'V' + (yTop + r) + 'Q' + x + ',' + yTop + ' ' + (x + r) + ',' + yTop + 'H' + (x + w - r) + 'Q' + (x + w) + ',' + yTop + ' ' + (x + w) + ',' + (yTop + r) + 'V' + yBase + 'Z"></path>';
}

function grafMeses() {
  const el = $('#graf-meses');
  if (!el || !S.historial) return;
  const datos = S.historial;
  const W = Math.max(280, el.clientWidth), H = 250, pL = 64, pR = 6, pT = 12, pB = 32;
  const max = Math.max(1, ...datos.map(d => Math.max(d.ing, d.egr)));
  const paso = pasoLindo(max / 4), tope = Math.ceil(max / paso) * paso;
  const y = v => pT + (H - pT - pB) * (1 - v / tope);
  const gw = (W - pL - pR) / datos.length, bw = Math.min(28, gw * 0.3);
  let s = '';
  for (let t = 0; t <= tope + 1; t += paso) {
    s += '<line x1="' + pL + '" x2="' + (W - pR) + '" y1="' + y(t) + '" y2="' + y(t) + '" stroke="var(--line)" stroke-width="1"></line>' +
      '<text x="' + (pL - 8) + '" y="' + (y(t) + 4) + '" text-anchor="end">' + (t ? corto(t) : '$ 0') + '</text>';
  }
  datos.forEach((d, i) => {
    const cx = pL + gw * (i + 0.5), saldo = d.ing - d.egr - (d.ahorro || 0), nombre = mesNombre(d.mes);
    const tip = mayus(nombre) + (d.actual ? ' (en curso)' : '') + '|Ingresos: ' + plata(d.ing) + '|Egresos: ' + plata(d.egr) +
      (d.ahorro ? '|Ahorro: ' + plata(d.ahorro) : '') + '|' + (saldo >= 0 ? 'Saldo a favor: ' : 'Saldo negativo: ') + plata(Math.abs(saldo));
    s += '<g class="grupo" data-tip="' + esc(tip) + '"><rect class="hit" x="' + (pL + gw * i + 2) + '" y="' + pT + '" width="' + (gw - 4) + '" height="' + (H - pT - pB) + '" rx="8"></rect>' +
      columna(cx - bw - 1, y(d.ing), bw, y(0), 'var(--c3)') + columna(cx + 1, y(d.egr), bw, y(0), 'var(--c2)') +
      '<text class="eje-x" x="' + cx + '" y="' + (H - 8) + '" text-anchor="middle"' + (d.actual ? ' style="font-weight:700"' : '') + '>' + nombre.slice(0, 3) + '</text></g>';
  });
  el.innerHTML = '<svg width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + ' ' + H + '">' + s + '</svg>';
}

function mostrarTip(e) {
  const tip = $('#tip');
  const t = e.target.closest && e.target.closest('[data-tip]');
  if (!t) { tip.hidden = true; return; }
  tip.innerHTML = t.getAttribute('data-tip').split('|').map((l, i) => i ? esc(l) : '<b>' + esc(l) + '</b>').join('<br>');
  tip.hidden = false;
  const w = tip.offsetWidth, h = tip.offsetHeight;
  tip.style.left = Math.min(window.innerWidth - w - 8, Math.max(8, e.clientX - w / 2)) + 'px';
  tip.style.top = Math.max(8, e.clientY - h - 16) + 'px';
}
document.addEventListener('pointermove', mostrarTip);
document.addEventListener('pointerdown', mostrarTip);
window.addEventListener('scroll', () => { $('#tip').hidden = true; }, { passive: true });
let resizeT;
window.addEventListener('resize', () => { clearTimeout(resizeT); resizeT = setTimeout(grafMeses, 150); });

// ------------------------------------------------------------------ gastos fijos
VISTAS.fijos = async () => {
  const r = await api('GET', '/api/resumen');
  S.resumen = r;
  S.tarjetas = r.tarjetas;
  const pagados = r.fijos.filter(f => f.pagado).length;
  const pendiente = r.fijos.filter(f => !f.pagado).reduce((a, f) => a + f.monto, 0);
  const lista = r.fijos.slice().sort((a, b) => (a.pagado - b.pagado) || (a.vence - b.vence));
  const sugs = SUG_FIJOS.filter(s => !r.fijos.some(f => f.nombre === s.n));
  return cabecera('Gastos fijos', 'Egresos que se repiten todos los meses') +
    '<section class="bloque"><div class="total-cab"><span class="muted">Total mensual</span><span class="grande-num num">' + plata(r.totales.fij) + '</span></div>' +
      (r.fijos.length ? '<div class="anillo-fila">' + anillo(pagados, r.fijos.length) + '<div><b>Pagaste ' + pagados + ' de ' + r.fijos.length + '</b><p class="muted">' +
        (pagados === r.fijos.length ? 'Todo al día este mes.' : 'Quedan ' + plata(pendiente) + ' por pagar.') + '</p></div></div>' : '') + '</section>' +
    '<section class="bloque">' +
      (lista.length ? '<p class="muted">Tocá el círculo cuando lo pagues. Tocá el nombre para editarlo.</p><div class="lista">' + lista.map(f => filaFijo(f)).join('') + '</div>'
        : '<p class="muted">Todavía no cargaste gastos fijos. Podés elegirlos de la lista de abajo.</p>') +
      '<button class="btn ancho" data-acc="nuevo-fijo">+ Agregar gasto fijo</button></section>' +
    (sugs.length ? '<section class="bloque"><h2>Gastos fijos frecuentes</h2><p class="muted">Tocá el que corresponda para agregarlo.</p><div class="sugs">' +
      sugs.map(s => '<button class="sug" data-acc="sug-fijo" data-n="' + esc(s.n) + '"><span aria-hidden="true">' + s.i + '</span>' + esc(s.n) + '</button>').join('') + '</div></section>' : '');
};

// ------------------------------------------------------------------ ingresos
VISTAS.ingresos = async () => {
  const r = await api('GET', '/api/resumen');
  S.resumen = r;
  S.tarjetas = r.tarjetas;
  const extra = await api('GET', '/api/movs?mes=' + r.mes + '&tipo=ingreso');
  S.movs = extra.items;
  const sugs = SUG_ING.filter(s => !r.ingresos.some(x => x.nombre === s.n));
  return cabecera('Ingresos', 'Ingresos de ' + r.mes_nombre) +
    '<section class="bloque"><div class="total-cab"><span class="muted">Total del mes</span><span class="grande-num num" style="color:var(--good)">' + plata(r.totales.ing) + '</span>' +
      (r.totales.ing_extra ? '<span class="muted">' + plata(r.totales.ing_fijos) + ' fijos + ' + plata(r.totales.ing_extra) + ' extra</span>' : '') + '</div></section>' +
    '<section class="bloque"><h2>Ingresos mensuales</h2>' +
      (r.ingresos.length ? '<p class="muted">Tocá el círculo cuando cobres. Si este mes cobraste otro monto, ponelo ahí y el saldo se ajusta.</p><div class="lista">' + r.ingresos.map(x => filaIngreso(x)).join('') + '</div>'
        : '<p class="muted">Cargá acá tu sueldo y cualquier otro ingreso que se repita todos los meses.</p>') +
      '<button class="btn ancho" data-acc="nuevo-ingreso">+ Agregar ingreso mensual</button></section>' +
    '<section class="bloque"><h2>Ingresos extra de ' + r.mes_nombre + '</h2><p class="muted">Plata que entró una sola vez: una venta, un trabajo puntual, un reintegro.</p>' +
      (extra.items.length ? '<div class="lista">' + extra.items.map(filaMov).join('') + '</div>' : '') +
      '<button class="btn sec ancho" data-acc="cargar-ingreso">+ Registrar ingreso extra</button></section>' +
    (sugs.length ? '<section class="bloque"><h2>Ingresos frecuentes</h2><div class="sugs">' +
      sugs.map(s => '<button class="sug" data-acc="sug-ing" data-n="' + esc(s.n) + '"><span aria-hidden="true">' + s.i + '</span>' + esc(s.n) + '</button>').join('') + '</div></section>' : '');
};

// ------------------------------------------------------------------ movimientos
VISTAS.movimientos = async () => {
  const hoyKey = (S.hoy || new Date().toISOString()).slice(0, 7);
  const mes = S.movMes || hoyKey;
  const r = await api('GET', '/api/movs?mes=' + mes + (S.movTipo ? '&tipo=' + S.movTipo : ''));
  S.movs = r.items;
  const meses = Array.from(new Set([hoyKey].concat(r.meses))).sort().reverse().slice(0, 12);
  if (!S.tarjetas) S.tarjetas = (await api('GET', '/api/tarjetas')).items;
  const total = r.items.filter(m => m.tipo === (S.movTipo || 'egreso') && !m.tarjeta_id).reduce((a, m) => a + m.monto, 0);
  const conTarjeta = r.items.filter(m => m.tarjeta_id).reduce((a, m) => a + m.monto, 0);
  let html = '', ult = '';
  r.items.forEach(m => {
    if (m.fecha !== ult) { if (ult) html += '</div>'; html += '<p class="fecha-grupo">' + nombreFecha(m.fecha) + '</p><div class="lista">'; ult = m.fecha; }
    html += filaMov(m);
  });
  if (ult) html += '</div>';
  const tipos = [['', 'Todo'], ['egreso', 'Egresos'], ['ingreso', 'Ingresos extra'], ['ahorro', 'Ahorros']];
  const etiqueta = { '': 'Egresos variables', egreso: 'Egresos variables', ingreso: 'Ingresos extra', ahorro: 'Ahorro e inversión' }[S.movTipo];
  return cabecera('Egresos y movimientos', 'Todo lo que cargaste, día por día') +
    '<div class="chips-mes" role="group" aria-label="Mes">' + meses.map(k => '<button data-acc="mov-mes" data-k="' + k + '" aria-pressed="' + (k === mes) + '">' + mayus(mesNombre(k)) + (k.slice(0, 4) !== hoyKey.slice(0, 4) ? ' ' + k.slice(0, 4) : '') + '</button>').join('') + '</div>' +
    '<div class="segmento" style="grid-template-columns:repeat(4,1fr)" role="group" aria-label="Tipo">' + tipos.map(([k, n]) => '<button data-acc="mov-tipo" data-k="' + k + '" aria-pressed="' + (k === S.movTipo) + '">' + n + '</button>').join('') + '</div>' +
    '<section class="bloque"><div class="total-cab"><span class="muted">' + etiqueta + ' de ' + mesNombre(mes) + (S.movTipo === 'ahorro' || S.movTipo === 'ingreso' ? '' : ' (efectivo y débito)') + '</span><span class="grande-num num">' + plata(total) + '</span>' +
      (conTarjeta ? '<span class="muted">Además compraste ' + plata(conTarjeta) + ' con tarjeta: cada cuota se cuenta en el mes en que se paga. <a href="#tarjetas">Ver tarjetas</a></span>' : '') + '</div>' +
      '<div class="acciones"><button class="btn" data-acc="cargar">+ Cargar un egreso</button><a class="btn sec" href="#tarjetas">💳 Tarjetas y cuotas</a></div></section>' +
    '<section class="bloque">' + (html || '<div class="vacio"><div class="ico">🧾</div><p class="muted">No hay movimientos cargados en este mes.</p></div>') + '</section>';
};

// ------------------------------------------------------------------ tarjetas
VISTAS.tarjetas = async () => {
  const r = await api('GET', '/api/tarjetas');
  S.tarjetas = r.items;
  const cab = cabecera('Tarjetas y cuotas', 'Lo que pagás cada mes con tarjeta de crédito');
  if (!r.items.length) return cab + '<section class="bloque vacio"><div class="ico">💳</div><h2>Agregá tu tarjeta</h2>' +
    '<p class="muted">Cargá tus compras en cuotas y la app te muestra cuánto pagás cada mes y cuánto tenés comprometido para los próximos.</p>' +
    '<button class="btn" data-acc="nueva-tarjeta">+ Agregar tarjeta</button></section>';
  const max = Math.max(1, ...r.compromisos.map(c => c.total));
  const totalMes = r.items.reduce((a, t) => a + t.total, 0);
  const filaCuota = c => '<div class="fila"><div class="ico" aria-hidden="true" style="--k:' + colorCat(c.cat) + '">' + (CATS[c.cat] || CATS.otros).i + '</div>' +
    '<button class="fila-txt" data-acc="editar-cuota" data-id="' + c.id + '"><b>' + esc(c.descr || (CATS[c.cat] || CATS.otros).n) + '</b><small>' +
    (c.cuota_n ? 'Cuota ' + c.cuota_n + ' de ' + c.cuotas + (c.cuotas > 1 ? ' · termina en ' + mesNombre(c.ultimo_mes) : '')
      : (c.cuotas > 1 ? c.cuotas + ' cuotas · ' : '') + 'se empieza a pagar en ' + mesNombre(c.primer_mes)) +
    ' · ' + esc(c.tarjeta) + '</small></button><span class="fila-monto num">' + plata(c.importe) + '</span></div>';
  return cab +
    '<section class="bloque"><div class="total-cab"><span class="muted">A pagar en ' + mesNombre(r.mes) + '</span><span class="grande-num num">' + plata(totalMes) + '</span></div>' +
      '<div class="lista">' + r.items.map(filaTarjeta).join('') + '</div>' +
      '<div class="acciones"><button class="btn" data-acc="cargar">+ Cargar compra</button><button class="btn sec" data-acc="nueva-tarjeta">+ Agregar tarjeta</button></div></section>' +
    '<section class="bloque"><h2>Comprometido en cuotas</h2><p class="muted">Lo que ya tenés que pagar en los próximos meses por compras hechas.</p><div class="barras-h">' +
      r.compromisos.map(c => '<div class="barra-h"><span class="mes">' + mayus(mesNombre(c.mes)).slice(0, 3) + '</span><div class="riel"><span style="width:' + (c.total / max * 100).toFixed(1) +
        '%;background:var(--c4)"></span></div><b class="num">' + plata(c.total) + '</b></div>').join('') + '</div></section>' +
    (r.en_curso.length ? '<section class="bloque"><h2>Cuotas de este mes</h2><div class="lista">' + r.en_curso.map(filaCuota).join('') + '</div></section>' : '') +
    (r.futuras.length ? '<section class="bloque"><h2>Compras que entran en próximos resúmenes</h2><div class="lista">' + r.futuras.map(filaCuota).join('') + '</div></section>' : '') +
    '<section class="bloque"><h2>Mis tarjetas</h2><div class="lista">' + r.items.map(t => '<div class="fila"><div class="ico" aria-hidden="true" style="--k:var(--c4)">💳</div>' +
      '<button class="fila-txt" data-acc="editar-tarjeta" data-id="' + t.id + '"><b>' + esc(t.nombre) + '</b><small>Cierra el día ' + t.cierre + ' · vence el día ' + t.vence + '</small></button></div>').join('') + '</div></section>';
};

// ------------------------------------------------------------------ logros
VISTAS.logros = async () => {
  const r = await api('GET', '/api/logros');
  S.racha = r.racha;
  const n = r.nivel;
  const umbrales = [0, 2, 5, 9, 13], desde = umbrales[n.numero - 1], hasta = n.siguiente ? umbrales[n.numero] : desde;
  const avance = hasta > desde ? Math.round((r.ganados - desde) / (hasta - desde) * 100) : 100;
  api('POST', '/api/logros/vistos').catch(() => {});
  return cabecera('Tus logros', 'Reconocimientos por ordenar tus cuentas, ahorrar y ser constante', r.racha) +
    '<section class="nivel"><span>Nivel ' + n.numero + '</span><h2 style="font-size:1.6rem">' + n.nombre + '</h2>' +
      '<p>' + r.ganados + ' de ' + r.total + ' logros' + (n.siguiente ? ' · ' + (n.faltan === 1 ? 'te falta 1 logro' : 'te faltan ' + n.faltan + ' logros') + ' para «' + n.siguiente + '»' : ' · ¡Llegaste al nivel máximo!') + '</p>' +
      '<div class="progreso"><span style="width:' + avance + '%"></span></div></section>' +
    '<section class="bloque"><div class="racha-grande"><span class="fuego">🔥</span><div><h2>' + (r.racha === 1 ? '1 día seguido' : r.racha + ' días seguidos') + '</h2>' +
      '<p class="muted">Cada día que anotás algo (o tocás «Hoy no gasté») suma a tu racha.</p></div></div></section>' +
    '<div class="medallas">' + r.items.map(x => '<div class="medalla ' + (x.ganado ? '' : 'bloqueada') + '"><div class="disco" aria-hidden="true">' + x.icono + '</div><b>' + esc(x.titulo) + '</b><small>' + esc(x.desc) + '</small>' +
      (x.ganado ? '<span class="chip good">Ganado el ' + fechaCorta(x.fecha) + '</span>' : x.progreso != null ? '<div class="progreso"><span style="width:' + Math.round(x.progreso / x.meta * 100) + '%"></span></div><small>' + x.progreso + ' de ' + x.meta + '</small>' : '') +
      '</div>').join('') + '</div>' +
    '<p class="muted chico centro">Los logros reconocen lo que vos hacés. La app no recomienda inversiones.</p>';
};

function festejar(lista) {
  if (!lista || !lista.length) return;
  const x = lista[0];
  const colores = ['var(--c1)', 'var(--c2)', 'var(--c3)', 'var(--c4)', 'var(--c5)', 'var(--c7)'];
  const confeti = Array.from({ length: 28 }, (_, i) => '<i class="confeti" style="left:' + (Math.random() * 100).toFixed(1) + '%;background:' + colores[i % colores.length] + ';animation-delay:' + (Math.random() * .5).toFixed(2) + 's"></i>').join('');
  $('#capa').innerHTML = '<div class="festejo" data-acc="cerrar-festejo"><div class="festejo-caja" role="dialog" aria-modal="true" aria-labelledby="fest-t">' + confeti +
    '<div class="disco" aria-hidden="true">' + x.icono + '</div><span class="muted">¡Nuevo logro!</span><h2 id="fest-t">' + esc(x.titulo) + '</h2><p>' + esc(x.desc) + '</p>' +
    (lista.length > 1 ? '<p class="muted">Y ganaste ' + (lista.length - 1) + ' más.</p>' : '') +
    '<button class="btn ancho" data-acc="cerrar-festejo">¡Genial!</button><button class="link" data-acc="ir-logros">Ver todos mis logros</button></div></div>';
}

// ------------------------------------------------------------------ avisos
VISTAS.avisos = async () => {
  const r = await api('GET', '/api/notifications');
  if (S.unread) { api('POST', '/api/notifications/read').catch(() => {}); S.unread = 0; }
  return cabecera('Avisos') +
    (pushSoportado() && Notification.permission !== 'granted' ? '<div class="aviso verde"><p>Activá las notificaciones para que los avisos te lleguen al celular.</p><button class="btn" data-acc="activar-avisos">Activar</button></div>' : '') +
    '<section class="bloque">' + (r.items.length ? '<div class="lista">' + r.items.map(n =>
      '<div class="fila"><div class="ico" aria-hidden="true">' + ({ logro: '🏅', vencimiento: '📅', diario: '✍️', resumen: '📊', cobro: '💼', pago: '💳', prueba: '⏳' }[n.kind] || '🔔') + '</div>' +
      '<a class="fila-txt" href="' + esc(n.url || '#inicio') + '" style="text-decoration:none;color:inherit"><b>' + esc(n.title) + '</b><small>' + esc(n.body) + '</small><small>' + fechaCorta((n.created_at || '').slice(0, 10)) + '</small></a></div>').join('') + '</div>'
      : '<div class="vacio"><div class="ico">🔔</div><p class="muted">Todavía no tenés avisos.</p></div>') + '</section>';
};

// ------------------------------------------------------------------ mi cuenta y ajustes
function selectHora(id, sel) {
  return '<select id="' + id + '">' + Array.from({ length: 16 }, (_, i) => i + 8).map(h => '<option value="' + h + '"' + (h === sel ? ' selected' : '') + '>' + pad(h) + ':00 hs</option>').join('') + '</select>';
}

function bloqueNotif() {
  if (!pushSoportado() && !(esIOS && !instalada())) return '<p class="muted">Este navegador no permite notificaciones. Probá desde el celular con la app instalada.</p>';
  if (esIOS && !instalada()) return '<div class="consejo ojo"><div class="ico">📱</div><div><h3>En iPhone, primero instalá la app</h3><p>Apple solo permite notificaciones a las apps agregadas a la pantalla de inicio. Instalala y activalas desde ahí.</p><button class="link" data-acc="instalar">Ver cómo instalarla</button></div></div>';
  if (Notification.permission === 'denied') return '<div class="consejo alerta"><div class="ico">🔕</div><div><h3>Las notificaciones están bloqueadas</h3><p>Habilitalas en los ajustes del celular o del navegador, para este sitio.</p></div></div>';
  if (Notification.permission === 'granted' && S.pushDevices) return '<div class="acciones"><span class="chip good" style="align-self:center">Activadas en este dispositivo</span><button class="btn sec" data-acc="probar-aviso">Mandarme una prueba</button></div>';
  return '<button class="btn ancho" data-acc="activar-avisos">🔔 Activar notificaciones</button>';
}

VISTAS.ajustes = async () => {
  await cargarMe();
  const u = S.me, c = u.cuenta;
  const estadoTxt = c.estado === 'activa' ? (c.hasta ? 'Suscripción activa hasta el ' + fechaCorta(c.hasta) : 'Cuenta activa') : c.estado === 'prueba' ? 'Prueba gratis: ' + (c.dias === 1 ? 'hoy es el último día' : 'quedan ' + c.dias + ' días') : 'Acceso en pausa';
  return cabecera('Mi cuenta', esc(u.email)) +
    '<section class="bloque"><div class="bloque-cab"><h2>Suscripción</h2><a class="link" href="#cuenta">Ver detalle</a></div><p>' + estadoTxt + '</p></section>' +
    '<section class="bloque"><h2>Recordatorios</h2>' +
      '<label class="interruptor"><span><b>Recordatorio diario</b><br><span class="muted chico">Si no anotaste nada en el día</span></span><input type="checkbox" id="av-diario" data-acc="pref" data-k="av_diario"' + (u.av_diario ? ' checked' : '') + '></label>' +
      '<div class="campo"><label for="aj-hora">Hora del recordatorio</label>' + selectHora('aj-hora', u.notify_hour) + '</div>' +
      '<label class="interruptor"><span><b>Vencimientos y cobros</b><br><span class="muted chico">El día antes, el mismo día y si se pasó</span></span><input type="checkbox" id="av-venc" data-acc="pref" data-k="av_vencimientos"' + (u.av_vencimientos ? ' checked' : '') + '></label>' +
      '<label class="interruptor"><span><b>Resumen del mes</b><br><span class="muted chico">El día 1, cómo cerró el mes anterior</span></span><input type="checkbox" id="av-res" data-acc="pref" data-k="av_resumen"' + (u.av_resumen ? ' checked' : '') + '></label>' +
      '<h3 style="margin-top:6px">Notificaciones en este dispositivo</h3>' + bloqueNotif() + '</section>' +
    '<section class="bloque"><h2>Meta de ahorro mensual</h2><p class="muted">Ponete una meta y la app te muestra cómo venís. Si la cumplís, ganás un logro.</p>' +
      '<form class="acciones" data-form="meta"><div class="campo" style="flex:1 1 200px"><label for="aj-meta" class="chico">Monto por mes</label><div class="monto-in"><span>$</span><input id="aj-meta" inputmode="numeric" value="' + fmtMonto(u.meta_ahorro) + '" placeholder="0"></div></div>' +
      '<button class="btn" type="submit" style="align-self:flex-end">Guardar</button></form></section>' +
    '<section class="bloque"><h2>Pantalla</h2>' +
      '<label class="interruptor"><span><b>Letra más grande</b></span><input type="checkbox" id="aj-grande" data-acc="pref" data-k="grande"' + (u.grande ? ' checked' : '') + '></label>' +
      (instalada() ? '' : '<button class="btn sec ancho" data-acc="instalar">📱 Instalar la app en el celular</button>') + '</section>' +
    '<section class="bloque"><h2>Tu nombre</h2><form class="acciones" data-form="nombre"><div class="campo" style="flex:1 1 200px"><input id="aj-nombre" value="' + esc(u.name) + '" aria-label="Tu nombre"></div><button class="btn" type="submit">Guardar</button></form></section>' +
    '<section class="bloque"><h2>Ayuda</h2><button class="btn sec ancho" data-acc="feedback">💬 Contanos qué mejorar</button>' +
      '<a class="btn sec ancho" href="/api/me/export" download>⬇️ Descargar mis datos</a>' +
      (u.demo ? '' : '<button class="btn sec ancho" data-acc="cambiar-pass">🔒 Cambiar contraseña</button>') + '</section>' +
    '<div class="acciones"><button class="btn sec" data-acc="salir">Cerrar sesión</button>' + (u.demo ? '' : '<button class="btn peligro" data-acc="borrar-cuenta">Borrar mi cuenta</button>') + '</div>';
};

VISTAS.cuenta = async () => {
  await cargarMe();
  const r = await api('GET', '/api/cuenta');
  const e = r.estado;
  const titulo = e.estado === 'activa' ? '✅ Suscripción activa' : e.estado === 'prueba' ? '⏳ Prueba gratis' : '⏸️ Acceso en pausa';
  const detalle = e.estado === 'activa' ? (e.hasta ? 'Al día hasta el ' + fechaCorta(e.hasta) + '.' : 'Tu cuenta no tiene vencimiento.')
    : e.estado === 'prueba' ? (e.dias === 1 ? 'Hoy es el último día de prueba.' : 'Te quedan ' + e.dias + ' días de prueba (hasta el ' + fechaCorta(e.hasta) + ').')
    : 'Tus datos siguen guardados. Suscribite para volver a cargar movimientos.';
  const pagar = r.mp_auto || r.mp_link;
  return cabecera('Suscripción') +
    '<section class="bloque"><h2>' + titulo + '</h2><p>' + detalle + '</p></section>' +
    (e.estado !== 'activa' || r.mp_status !== 'authorized' ? '<section class="bloque"><h2>Plan mensual</h2><p class="grande-num" style="font-family:var(--f-display);font-size:2.2rem;font-weight:700">' + plata(r.precio) + '<span class="muted" style="font-size:1rem;font-weight:400"> por mes</span></p>' +
      '<p class="muted">Incluye todo: carga ilimitada, recordatorios, gráficos y logros. Se cobra automáticamente cada mes y podés darla de baja cuando quieras.' + (e.estado === 'prueba' ? ' Si te suscribís ahora, el primer mes empieza cuando termina la prueba.' : '') + '</p>' +
      (pagar ? '<button class="btn mp ancho xl" data-acc="suscribir">Suscribirme con Mercado Pago</button>' : '') +
      (r.alias ? '<div class="consejo"><div class="ico">🏦</div><div><h3>También por transferencia</h3><p>Alias: <b>' + esc(r.alias) + '</b>. Mandá el comprobante' + (r.contacto ? ' a ' + esc(r.contacto) : '') + ' y activamos tu mes.</p></div></div>' : '') +
      (!pagar && !r.alias ? '<p class="muted">Pronto vas a poder suscribirte desde acá.' + (r.contacto ? ' Mientras tanto, escribinos a ' + esc(r.contacto) + '.' : '') + '</p>' : '') + '</section>' : '') +
    (r.mp_status === 'authorized' ? '<section class="bloque"><h2>Débito automático</h2><p class="muted">Tu suscripción de Mercado Pago está activa.</p><button class="btn peligro" data-acc="cancelar-sus">Dar de baja la suscripción</button></section>' : '') +
    (r.pagos.length ? '<section class="bloque"><h2>Pagos</h2><div class="lista">' + r.pagos.map(p => '<div class="fila"><div class="ico">💳</div><div class="fila-txt"><b>' + (p.monto ? plata(p.monto) : 'Pago registrado') + '</b><small>' + fechaCorta((p.created_at || '').slice(0, 10)) + ' · cubre hasta el ' + fechaCorta(p.hasta) + '</small></div></div>').join('') + '</div></section>' : '');
};

// ------------------------------------------------------------------ administración
VISTAS.admin = async () => {
  if (S.me.role !== 'admin') return cabecera('') + '<p>Sección solo para administración.</p>';
  const r = await api('GET', '/api/admin');
  const s = r.settings, R = r.resumen;
  const estado = c => c.estado === 'activa' ? '<span class="chip good">Activa</span>' : c.estado === 'prueba' ? '<span class="chip sun">Prueba · ' + c.dias + ' d</span>' : '<span class="chip bad">Vencida</span>';
  return cabecera('Administración') +
    '<div class="tiles"><div class="tile"><span class="muted">Cuentas</span><b>' + R.total + '</b></div><div class="tile"><span class="muted">Usaron la app (7 días)</span><b>' + R.activos7 + '</b></div>' +
      '<div class="tile"><span class="muted">En prueba</span><b>' + R.prueba + '</b></div><div class="tile"><span class="muted">Pagando</span><b>' + R.activa + '</b></div>' +
      '<div class="tile"><span class="muted">Vencidas</span><b>' + R.vencida + '</b></div><div class="tile"><span class="muted">Cobrado este mes</span><b>' + plata(R.cobrado_mes) + '</b></div></div>' +
    '<section class="bloque"><h2>Personas</h2><div class="tabla-wrap"><table><thead><tr><th>Nombre</th><th>Estado</th><th>Movs.</th><th>Avisos</th><th>Última vez</th><th></th></tr></thead><tbody>' +
      (r.users.length ? r.users.map(u => '<tr><td><b>' + esc(u.name) + '</b><br><span class="muted">' + esc(u.email) + '</span></td><td>' + estado(u.cuenta) + (u.mp_status ? '<br><span class="muted chico">MP: ' + esc(u.mp_status) + '</span>' : '') + '</td>' +
        '<td>' + u.movs + '</td><td>' + (u.push ? '🔔 ' + u.push : '—') + '</td><td>' + fechaCorta((u.last_seen || '').slice(0, 10)) + '</td>' +
        '<td><div class="acciones"><button class="btn" data-acc="adm-pago" data-id="' + u.id + '">+1 mes pago</button><button class="btn sec" data-acc="adm-prueba" data-id="' + u.id + '">+7 días prueba</button><button class="btn sec" data-acc="adm-reset" data-mail="' + esc(u.email) + '">Link clave</button></div></td></tr>').join('')
        : '<tr><td colspan="6" class="muted">Todavía no se registró nadie.</td></tr>') +
    '</tbody></table></div></section>' +
    '<form class="bloque" data-form="admin-settings"><h2>Cobro</h2>' +
      '<p class="muted chico">' + (r.mp_auto ? '✅ Mercado Pago conectado: las suscripciones y los pagos se registran solos.' : 'Mercado Pago no está conectado (falta CUENTAS_MP_TOKEN). Podés pegar un link de suscripción armado en Mercado Pago y marcar los pagos a mano.') + '</p>' +
      '<div class="campo"><label for="ad-precio">Precio mensual ($)</label><input id="ad-precio" inputmode="numeric" value="' + esc(s.precio_mensual) + '"></div>' +
      '<div class="campo"><label for="ad-dias">Días de prueba gratis</label><input id="ad-dias" inputmode="numeric" value="' + esc(s.dias_prueba) + '"></div>' +
      (r.mp_auto ? '' : '<div class="campo"><label for="ad-link">Link de suscripción de Mercado Pago</label><input id="ad-link" value="' + esc(s.mp_link) + '" placeholder="https://www.mercadopago.com.ar/subscriptions/checkout?..."></div>') +
      '<div class="campo"><label for="ad-alias">Alias para transferencias (opcional)</label><input id="ad-alias" value="' + esc(s.alias_transferencia) + '"></div>' +
      '<div class="campo"><label for="ad-mail">Mail de contacto</label><input id="ad-mail" type="email" value="' + esc(s.contact_email) + '"></div>' +
      '<p class="error" hidden></p><button class="btn" type="submit">Guardar</button></form>' +
    '<section class="bloque"><h2>Comentarios</h2>' + (r.feedback.length ? '<div class="lista">' + r.feedback.map(f =>
      '<div class="fila"><div class="ico">' + (f.kind === 'problema' ? '⚠️' : '💡') + '</div><div class="fila-txt"><b>' + esc(f.user_name || 'Alguien') + '</b><small>' + esc(f.text) + '</small><small>' + fechaCorta((f.created_at || '').slice(0, 10)) + '</small></div>' +
      (f.status === 'nuevo' ? '<button class="btn sec" data-acc="adm-visto" data-id="' + f.id + '">Visto</button>' : '') + '</div>').join('') + '</div>' : '<p class="muted">Sin comentarios por ahora.</p>') + '</section>' +
    '<p class="muted chico">Notificaciones: ' + (r.mail ? 'mail configurado' : 'mail sin configurar (los links para recuperar la clave se generan desde acá)') + '.</p>';
};

// ------------------------------------------------------------------ hojas (formularios abajo)
let hojaAct = null;

function hoja(titulo, cuerpo, enviar) {
  hojaAct = { enviar };
  $('#capa').innerHTML = '<div class="velo" data-acc="velo"><form class="hoja" role="dialog" aria-modal="true" aria-labelledby="hoja-t" novalidate data-form="hoja">' +
    '<div class="hoja-cab"><h2 id="hoja-t">' + titulo + '</h2><button type="button" class="cerrar" data-acc="cerrar" aria-label="Cerrar">×</button></div>' + cuerpo + '</form></div>';
  // si el nombre ya viene completo (una sugerencia), el cursor va directo al monto
  const nombre = $('#f-nombre');
  const f = nombre && nombre.value ? $('#f-monto') : $('#capa input:not([type=checkbox]):not([type=date])');
  if (f) f.focus();
}
function cerrarHoja() { hojaAct = null; if ($('#capa')) $('#capa').innerHTML = ''; }

function catsHtml(cats, sel) {
  return '<div class="cats" role="group" aria-label="Categoría">' + Object.entries(cats).map(([k, v]) =>
    '<button type="button" data-acc="cat" data-k="' + k + '" aria-pressed="' + (k === sel) + '"><span aria-hidden="true">' + v.i + '</span>' + v.n + '</button>').join('') + '</div>';
}
const catElegida = () => { const b = $('#capa .cats [aria-pressed="true"]'); return b ? b.dataset.k : null; };
const campoMonto = (label, v) => '<div class="campo"><label for="f-monto">' + label + '</label><div class="monto-in"><span>$</span><input id="f-monto" inputmode="numeric" autocomplete="off" value="' + fmtMonto(v) + '" placeholder="0"></div></div>';
const botonesHoja = (editando, txt) => '<p class="error" hidden></p><div class="acciones"><button class="btn" type="submit">' + (txt || (editando ? 'Guardar cambios' : 'Guardar')) + '</button>' +
  (editando ? '<button class="btn sec" type="button" data-acc="borrar">Borrar</button>' : '') + '</div>';

async function asegurarTarjetas(forzar) {
  if (forzar || !S.tarjetas) S.tarjetas = (await api('GET', '/api/tarjetas')).items;
  return S.tarjetas;
}

async function hojaMov(tipo, m, previo) {
  const ed = !!m;
  tipo = m ? m.tipo : tipo;
  const tarjetas = tipo === 'egreso' ? await asegurarTarjetas() : [];
  const v = previo || {};
  const pago = v.pago != null ? v.pago : (m && m.tarjeta_id) || '';
  const cuotas = v.cuotas || (m && m.cuotas) || 1;
  const titulo = { egreso: ed ? 'Editar egreso' : 'Cargar egreso', ingreso: ed ? 'Editar ingreso extra' : 'Ingreso extra', ahorro: ed ? 'Editar ahorro' : 'Ahorro o inversión' }[tipo];
  const seg = ed ? '' : '<div class="segmento" role="group" aria-label="Tipo de movimiento">' + [['egreso', 'Egreso'], ['ingreso', 'Ingreso extra'], ['ahorro', 'Ahorro']].map(([k, n]) =>
    '<button type="button" data-acc="tipo-mov" data-k="' + k + '" aria-pressed="' + (k === tipo) + '">' + n + '</button>').join('') + '</div>';
  const frec = !ed && !previo && tipo === 'egreso' && (S.frecuentes || []).length
    ? '<div class="frecuentes" aria-label="Tus gastos frecuentes">' + S.frecuentes.map((f, i) => '<button type="button" class="sug" data-acc="frecuente-hoja" data-i="' + i + '"><span aria-hidden="true">' +
      (CATS[f.cat] || CATS.otros).i + '</span>' + esc(f.descr) + '</button>').join('') + '</div>' : '';
  let cuerpo = seg + frec + campoMonto(tipo === 'egreso' ? 'Monto' : tipo === 'ingreso' ? '¿Cuánto entró?' : '¿Cuánto apartaste?', v.monto || (m && (m.precio || m.monto)));
  if (tipo === 'egreso') {
    const desc = v.desc != null ? v.desc : (m && m.descuento) || '', inte = v.inte != null ? v.inte : (m && m.interes) || '';
    cuerpo += '<div class="campo"><span class="lab">¿Cómo pagaste?</span><div class="pagos" role="group" aria-label="Medio de pago">' +
      '<button type="button" data-acc="pago" data-k="" aria-pressed="' + (!pago) + '">💵 Efectivo o débito</button>' +
      tarjetas.map(t => '<button type="button" data-acc="pago" data-k="' + t.id + '" aria-pressed="' + (+pago === t.id) + '">💳 ' + esc(t.nombre) + '</button>').join('') +
      '<button type="button" data-acc="tarjeta-desde-mov">+ Agregar tarjeta</button></div></div>' +
      '<div class="campo" id="bloque-cuotas"' + (pago ? '' : ' hidden') + '><span class="lab">Cuotas</span><div class="pagos" role="group" aria-label="Cuotas">' +
        [1, 3, 6, 9, 12, 18, 24].map(n => '<button type="button" data-acc="cuotas" data-k="' + n + '" aria-pressed="' + (n === +cuotas) + '">' + (n === 1 ? '1 pago' : n) + '</button>').join('') +
        '<input id="f-cuotas" type="number" inputmode="numeric" min="1" max="72" value="' + cuotas + '" aria-label="Otra cantidad de cuotas" class="mini-in"></div></div>' +
      '<details class="porcentajes"' + (desc || inte ? ' open' : '') + '><summary>¿Tuvo descuento, reintegro o interés?</summary><div class="pct-campos">' +
        '<div class="campo"><label for="f-desc-pct">Descuento o reintegro</label><div class="pct-in"><input id="f-desc-pct" inputmode="decimal" value="' + desc + '" placeholder="0"><span>%</span></div></div>' +
        '<div class="campo"><label for="f-int-pct">Interés o recargo</label><div class="pct-in"><input id="f-int-pct" inputmode="decimal" value="' + inte + '" placeholder="0"><span>%</span></div></div></div></details>' +
      '<div class="calculo" id="f-calculo" hidden></div>' +
      '<div class="campo"><span class="lab">Categoría</span>' + catsHtml(CATS, v.cat || (m ? m.cat : 'super')) + '</div>';
  }
  if (tipo === 'ahorro') cuerpo += '<div class="campo"><span class="lab">¿Es ahorro o inversión?</span>' + catsHtml(CATS_AHORRO, m ? m.cat : 'ahorro') + '</div>' +
    '<p class="muted chico">Registrá lo que separaste: una cuenta aparte, dólares, un plazo fijo u otra inversión. La app solo lo registra; no recomienda inversiones.</p>';
  const ph = { egreso: 'Ej.: verdulería, heladera, regalo para Sofi', ingreso: 'Ej.: venta de ropa, trabajo puntual', ahorro: 'Ej.: plazo fijo, compra de dólares' }[tipo];
  cuerpo += '<div class="campo"><label for="f-desc">Descripción <span class="muted">(opcional)</span></label><input id="f-desc" maxlength="80" value="' + esc(v.descr != null ? v.descr : m ? m.descr : '') + '" placeholder="' + ph + '"></div>' +
    '<div class="campo"><label for="f-fecha">Fecha</label><input id="f-fecha" type="date" value="' + (v.fecha || (m ? m.fecha : S.hoy || '')) + '"></div>' + botonesHoja(ed);
  hoja(titulo, cuerpo, {
    async guardar() {
      const datos = { tipo: hojaAct.tipo, monto: leerMonto($('#f-monto').value), cat: catElegida(), descr: $('#f-desc').value, fecha: $('#f-fecha').value };
      if (!datos.monto) throw new Error('Ingresá el monto en pesos.');
      if (hojaAct.tipo === 'egreso') {
        Object.assign(datos, { tarjeta_id: hojaAct.pago || null, cuotas: hojaAct.pago ? Math.max(1, +$('#f-cuotas').value || 1) : 1,
          descuento: leerPct($('#f-desc-pct').value), interes: leerPct($('#f-int-pct').value) });
        if (datos.descuento >= 100) throw new Error('El descuento tiene que ser menor a 100%.');
      }
      const r = ed ? await api('PUT', '/api/movs/' + m.id, datos) : await api('POST', '/api/movs', datos);
      return [ed ? 'Cambios guardados' : 'Registrado', r];
    },
    borrar: ed ? () => api('DELETE', '/api/movs/' + m.id) : null
  });
  Object.assign(hojaAct, { tipo, pago: pago ? +pago : '', editando: m });
  if (tipo === 'egreso') calcular();
}

function borradorMov() {
  const val = id => { const el = $(id); return el ? el.value : undefined; };
  return { monto: leerMonto(val('#f-monto')), desc: val('#f-desc-pct'), inte: val('#f-int-pct'), cuotas: val('#f-cuotas'),
    descr: val('#f-desc'), fecha: val('#f-fecha'), cat: catElegida(), pago: hojaAct.pago };
}

// muestra el total con descuento o interés, el valor de cada cuota y en qué mes se paga
function calcular() {
  const box = $('#f-calculo');
  if (!box || !hojaAct) return;
  const precio = leerMonto($('#f-monto').value), desc = leerPct($('#f-desc-pct').value), inte = leerPct($('#f-int-pct').value);
  const t = hojaAct.pago ? (S.tarjetas || []).find(x => x.id === hojaAct.pago) : null;
  const n = t ? Math.max(1, +$('#f-cuotas').value || 1) : 1;
  if (!precio || (!t && !desc && !inte)) { box.hidden = true; return; }
  const total = precioFinal(precio, desc, inte), conDesc = precioFinal(precio, desc, 0);
  const lineas = [];
  if (desc || inte) lineas.push('Total final: <b>' + plata(total) + '</b>' + (desc ? ' · ahorrás ' + plata(precio - conDesc) : '') + (inte ? ' · el interés suma ' + plata(total - conDesc) : ''));
  if (t) {
    const f = $('#f-fecha').value || S.hoy;
    const dia = +f.slice(8, 10), ultimoDia = new Date(+f.slice(0, 4), +f.slice(5, 7), 0).getDate();
    const primer = mesMas(f.slice(0, 7), dia <= Math.min(t.cierre, ultimoDia) ? 1 : 2), ultimo = mesMas(primer, n - 1);
    lineas.push(n > 1 ? '<b>' + n + ' cuotas de ' + plata(total / n) + '</b>' : 'En 1 pago: <b>' + plata(total) + '</b>');
    lineas.push((n > 1 ? 'La primera cuota se paga en <b>' : 'Se paga en <b>') + mesNombre(primer) + '</b>' +
      (n > 1 ? ' y la última en <b>' + mesNombre(ultimo) + (ultimo.slice(0, 4) !== primer.slice(0, 4) ? ' ' + ultimo.slice(0, 4) : '') + '</b>' : '') + '.');
  }
  box.innerHTML = lineas.map(l => '<p>' + l + '</p>').join('');
  box.hidden = false;
}

function hojaTarjeta(t, alGuardar) {
  const ed = !!(t && t.id);
  const sugs = ['Visa', 'Mastercard', 'American Express', 'Naranja X', 'Cabal'];
  hoja(ed ? 'Editar tarjeta' : 'Nueva tarjeta',
    (ed ? '' : '<div class="sugs">' + sugs.map(n => '<button type="button" class="sug" data-acc="sug-tarjeta" data-n="' + n + '">💳 ' + n + '</button>').join('') + '</div>') +
    '<div class="campo"><label for="f-nombre">Nombre</label><input id="f-nombre" maxlength="40" value="' + esc(t ? t.nombre : '') + '" placeholder="Ej.: Visa del Galicia"></div>' +
    '<div class="campo"><label for="f-cierre">Día de cierre</label><input id="f-cierre" type="number" inputmode="numeric" min="1" max="31" value="' + (t ? t.cierre : 24) + '"></div>' +
    '<div class="campo"><label for="f-vence">Día de vencimiento</label><input id="f-vence" type="number" inputmode="numeric" min="1" max="31" value="' + (t ? t.vence : 5) + '"></div>' +
    '<p class="muted chico">Los dos días figuran en el resumen de la tarjeta. Lo que comprás hasta el cierre se paga en el vencimiento del mes siguiente.</p>' + botonesHoja(ed), {
    async guardar() {
      const datos = { nombre: $('#f-nombre').value, cierre: +$('#f-cierre').value, vence: +$('#f-vence').value };
      if (!datos.nombre.trim()) throw new Error('Ingresá el nombre de la tarjeta.');
      const r = ed ? await api('PUT', '/api/tarjetas/' + t.id, datos) : await api('POST', '/api/tarjetas', datos);
      await asegurarTarjetas(true);
      if (alGuardar) { await alGuardar(r.id); return null; }
      return [ed ? 'Cambios guardados' : 'Tarjeta agregada', r];
    },
    borrar: ed ? async () => { await api('DELETE', '/api/tarjetas/' + t.id); await asegurarTarjetas(true); } : null
  });
}

function hojaPagarTarjeta(t) {
  hoja('Pagar ' + esc(t.nombre), campoMonto('¿Cuánto pagaste del resumen?', t.a_pagar) +
    '<p class="muted chico">Si el resumen vino con otro monto (impuestos, intereses, otras compras), poné el monto real.</p>' + botonesHoja(false, 'Marcar como pagada'), {
    async guardar() {
      const r = await api('POST', '/api/tarjetas/' + t.id + '/pagar', { monto: leerMonto($('#f-monto').value) });
      return ['Tarjeta ' + t.nombre + ': pagada', r];
    }
  });
}

function hojaFijo(f, sug) {
  const ed = !!(f && f.id);
  hoja(ed ? 'Editar gasto fijo' : 'Nuevo gasto fijo',
    '<div class="campo"><label for="f-nombre">Concepto</label><input id="f-nombre" maxlength="60" value="' + esc(f ? f.nombre : '') + '" placeholder="Ej.: Luz, Prepaga"></div>' +
    campoMonto('Monto mensual aproximado', f && f.monto) +
    '<div class="campo"><label for="f-dia">Día de vencimiento</label><input id="f-dia" type="number" inputmode="numeric" min="1" max="31" value="' + (f && f.dia || 10) + '"></div>' +
    '<div class="campo"><span class="lab">Categoría</span>' + catsHtml(CATS, (f && f.cat) || (sug && sug.c) || 'servicios') + '</div>' + botonesHoja(ed), {
    async guardar() {
      const datos = { nombre: $('#f-nombre').value, monto: leerMonto($('#f-monto').value), dia: +$('#f-dia').value || 1, cat: catElegida() };
      if (!datos.nombre.trim()) throw new Error('Ingresá el concepto.');
      if (!datos.monto) throw new Error('Ingresá el monto en pesos.');
      const r = ed ? await api('PUT', '/api/fijos/' + f.id, datos) : await api('POST', '/api/fijos', datos);
      return [ed ? 'Cambios guardados' : 'Agregado', r];
    },
    borrar: ed ? () => api('DELETE', '/api/fijos/' + f.id) : null
  });
}

function hojaIngreso(x) {
  const ed = !!(x && x.id);
  hoja(ed ? 'Editar ingreso' : 'Nuevo ingreso mensual',
    '<div class="campo"><label for="f-nombre">Concepto</label><input id="f-nombre" maxlength="60" value="' + esc(x ? x.nombre : '') + '" placeholder="Ej.: Sueldo"></div>' +
    campoMonto('Monto mensual', x && x.monto) +
    '<div class="campo"><label for="f-dia">Día de cobro</label><input id="f-dia" type="number" inputmode="numeric" min="1" max="31" value="' + (x && x.dia || 1) + '"></div>' + botonesHoja(ed), {
    async guardar() {
      const datos = { nombre: $('#f-nombre').value, monto: leerMonto($('#f-monto').value), dia: +$('#f-dia').value || 1 };
      if (!datos.nombre.trim()) throw new Error('Ingresá el concepto.');
      if (!datos.monto) throw new Error('Ingresá el monto en pesos.');
      const r = ed ? await api('PUT', '/api/ingresos/' + x.id, datos) : await api('POST', '/api/ingresos', datos);
      return [ed ? 'Cambios guardados' : 'Agregado', r];
    },
    borrar: ed ? () => api('DELETE', '/api/ingresos/' + x.id) : null
  });
}

function hojaPagar(f) {
  hoja('Pagar ' + esc(f.nombre), campoMonto('¿Cuánto pagaste este mes?', f.monto) +
    '<label class="casilla"><input type="checkbox" id="f-actualizar"><span>Usar este monto como habitual para los próximos meses</span></label>' + botonesHoja(false, 'Marcar como pagado'), {
    async guardar() {
      const monto = leerMonto($('#f-monto').value);
      if (!monto) throw new Error('Ingresá el monto en pesos.');
      const r = await api('POST', '/api/fijos/' + f.id + '/pagar', { monto, actualizar: $('#f-actualizar').checked });
      return [f.nombre + ': pagado', r];
    }
  });
}

function hojaCobrar(x) {
  hoja('Cobro de ' + esc(x.nombre), campoMonto('¿Cuánto cobraste este mes?', x.monto) +
    '<p class="muted chico">Si cobrás distinto cada mes, poné el monto real: el saldo del mes se calcula con este.</p>' + botonesHoja(false, 'Marcar como cobrado'), {
    async guardar() {
      const r = await api('POST', '/api/ingresos/' + x.id + '/cobrar', { monto: leerMonto($('#f-monto').value) });
      return [x.nombre + ': cobrado', r];
    }
  });
}

function hojaMas() {
  const it = (href, ico, txt) => '<a class="fila" href="' + href + '" data-acc="cerrar" style="text-decoration:none;color:inherit"><div class="ico" aria-hidden="true">' + ico + '</div><div class="fila-txt"><b>' + txt + '</b></div></a>';
  hoja('Más', '<div class="lista">' + it('#tarjetas', '💳', 'Tarjetas y cuotas') + it('#logros', '🏅', 'Mis logros') + it('#avisos', '🔔', 'Avisos') +
    it('#ajustes', '⚙️', 'Mi cuenta y recordatorios') + it('#cuenta', '⭐', 'Suscripción') + (S.me.role === 'admin' ? it('#admin', '🛡️', 'Administración') : '') + '</div>' +
    (instalada() ? '' : '<button type="button" class="btn sec ancho" data-acc="instalar">📱 Instalar la app</button>'), {});
}

function hojaPaywall() {
  hoja('Tu prueba terminó', '<p>Para seguir cargando movimientos, suscribite. <b>Tus datos siguen guardados</b> y podés verlos cuando quieras.</p>' +
    '<a class="btn ancho xl" href="#cuenta" data-acc="cerrar">Ver cómo suscribirme</a>', {});
}

function guiaInstalar() {
  const link = location.origin + '/';
  const copiar = '<div class="acciones"><input class="campo" readonly value="' + esc(link) + '" aria-label="Link de la app" style="flex:1 1 200px;font:inherit;padding:12px;border-radius:12px;border:2px solid var(--line);background:var(--surface);color:var(--ink)"><button type="button" class="btn sec" data-acc="copiar-link">Copiar link</button></div>';
  if (instalada()) return '<p>✅ Ya estás usando la app instalada.</p>';
  if (esIOS) return '<h3>En iPhone o iPad</h3><ol class="guia">' +
    '<li><span>Abrí este link en <b>Safari</b> (la brújula azul). Si estás en otra app, copiá el link y pegalo en Safari.</span></li>' +
    '<li><span>Tocá el botón <b>Compartir</b> ' + IC.compartir + ' (abajo en el centro, o arriba a la derecha en iPad).</span></li>' +
    '<li><span>Bajá y tocá <b>«Agregar a inicio»</b>. Después, <b>«Agregar»</b>.</span></li>' +
    '<li><span>Listo: abrí <b>Cuentas Claras</b> desde el ícono nuevo y activá las notificaciones en «Mi cuenta».</span></li></ol>' + copiar;
  if (esAndroid) return '<h3>En Android</h3>' + (instalarAndroid ? '<button type="button" class="btn ancho xl" data-acc="instalar-ya">📲 Instalar ahora</button><p class="muted chico">Si no aparece, seguí estos pasos:</p>' : '') +
    '<ol class="guia"><li><span>Abrí este link en <b>Chrome</b>.</span></li><li><span>Tocá los <b>tres puntitos ⋮</b> arriba a la derecha.</span></li>' +
    '<li><span>Tocá <b>«Instalar app»</b> o <b>«Agregar a la pantalla principal»</b>.</span></li><li><span>Listo: abrila desde el ícono de Cuentas Claras.</span></li></ol>' + copiar;
  return '<h3>En la compu</h3><p>Podés usarla directo desde el navegador. En Chrome o Edge, tocá el ícono de instalar (una pantallita con una flecha) en la barra de direcciones para tenerla como programa.</p>' +
    '<p class="muted">Para el celular, mandate este link y seguí los pasos desde ahí:</p>' + copiar;
}
function hojaInstalar() { hoja('Instalar la app', guiaInstalar(), {}); }

function hojaFeedback() {
  hoja('Contanos qué mejorar', '<div class="segmento" role="group" aria-label="Tipo">' + [['idea', 'Una idea'], ['problema', 'Un problema'], ['otro', 'Otra cosa']].map(([k, n], i) =>
    '<button type="button" data-acc="fb-tipo" data-k="' + k + '" aria-pressed="' + (i === 0) + '">' + n + '</button>').join('') + '</div>' +
    '<div class="campo"><label for="f-texto">Contanos</label><textarea id="f-texto" maxlength="2000"></textarea></div>' + botonesHoja(false, 'Enviar'), {
    async guardar() {
      const b = $('#capa .segmento [aria-pressed="true"]');
      await api('POST', '/api/feedback', { kind: b ? b.dataset.k : 'idea', text: $('#f-texto').value });
      return ['¡Gracias! Lo vamos a leer'];
    }
  });
}

function hojaPassword() {
  hoja('Cambiar contraseña', '<div class="campo"><label for="f-actual">Contraseña actual</label><input id="f-actual" type="password" autocomplete="current-password"></div>' +
    '<div class="campo"><label for="f-nueva">Contraseña nueva <span class="muted">(mínimo 8)</span></label><input id="f-nueva" type="password" autocomplete="new-password"></div>' + botonesHoja(false), {
    async guardar() { await api('POST', '/api/me/password', { current: $('#f-actual').value, new: $('#f-nueva').value }); return ['Contraseña cambiada']; }
  });
}

function hojaBorrarCuenta() {
  hoja('Borrar mi cuenta', '<p>Se borran <b>todos tus datos</b> y no se pueden recuperar. Si tenés una suscripción, se da de baja.</p>' +
    '<div class="campo"><label for="f-pass">Escribí tu contraseña para confirmar</label><input id="f-pass" type="password" autocomplete="current-password"></div>' +
    '<p class="error" hidden></p><button class="btn peligro ancho" type="submit">Borrar todo definitivamente</button>', {
    async guardar() { await api('DELETE', '/api/me', { password: $('#f-pass').value }); S.me = null; location.hash = ''; return ['Tu cuenta fue borrada']; }
  });
}

function hojaTerminos() {
  const prev = $('#capa').innerHTML;
  hoja('Términos y privacidad', '<div style="display:flex;flex-direction:column;gap:12px">' +
    '<p><b>Qué guardamos.</b> Tu nombre, tu mail y lo que cargás (ingresos, gastos, ahorros). La contraseña se guarda cifrada: nadie puede verla.</p>' +
    '<p><b>Para qué.</b> Solo para mostrarte tus cuentas y mandarte los recordatorios que elijas. No vendemos ni compartimos tus datos con nadie.</p>' +
    '<p><b>Tus derechos.</b> Podés descargar tus datos o borrar tu cuenta cuando quieras desde «Mi cuenta» (Ley 25.326 de Protección de Datos Personales).</p>' +
    '<p><b>Suscripción.</b> Después de la prueba gratis, el uso se paga por mes. Podés darte de baja cuando quieras; no hay permanencia.</p>' +
    '<p><b>Aclaración.</b> Cuentas Claras es una herramienta para ordenar tus finanzas. No da asesoramiento financiero ni recomienda inversiones.</p></div>' +
    '<button type="button" class="btn ancho" data-acc="cerrar">Entendido</button>', {});
  hojaAct.volver = prev;
}

async function activarAvisos() {
  if (esIOS && !instalada()) return hojaInstalar();
  if (!pushSoportado()) return toast('Este navegador no permite notificaciones');
  try {
    const perm = await Notification.requestPermission();
    if (perm !== 'granted') return toast('Sin permiso no te podemos avisar. Podés activarlo después.');
    const reg = await navigator.serviceWorker.ready;
    let sub = await reg.pushManager.getSubscription();
    if (!sub) {
      const raw = atob(S.vapid.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - S.vapid.length % 4) % 4));
      sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: Uint8Array.from(raw, c => c.charCodeAt(0)) });
    }
    await api('POST', '/api/push/subscribe', { subscription: sub.toJSON() });
    S.pushDevices = Math.max(1, S.pushDevices + 1);
    toast('¡Listo! Te van a llegar los recordatorios');
    vistaActual ? refrescar() : onboarding();
  } catch (e) { toast('No se pudieron activar: ' + e.message); }
}

// ------------------------------------------------------------------ acciones (un solo manejador de clics)
async function despuesDeGuardar(res) {
  if (res === null) return;          // ya se abrió la hoja siguiente (volver a la compra después de agregar una tarjeta)
  const [msg, r] = res || [];
  cerrarHoja();
  if (msg) toast(msg);
  if (vistaActual) await refrescar(); else if (S.me && !S.me.onboarded) onboarding();
  if (r && r.logros && r.logros.length) { festejar(r.logros); api('POST', '/api/logros/vistos').catch(() => {}); }
}

const ACC = {
  cargar: () => hojaMov('egreso'),
  'cargar-ahorro': () => hojaMov('ahorro'),
  'cargar-ingreso': () => hojaMov('ingreso'),
  'tipo-mov': el => { const t = el.dataset.k; cerrarHoja(); hojaMov(t); },
  pago(el) {
    el.parentElement.querySelectorAll('[data-acc=pago]').forEach(b => b.setAttribute('aria-pressed', b === el));
    hojaAct.pago = el.dataset.k ? +el.dataset.k : '';
    $('#bloque-cuotas').hidden = !hojaAct.pago;
    calcular();
  },
  cuotas(el) {
    el.parentElement.querySelectorAll('[data-acc=cuotas]').forEach(b => b.setAttribute('aria-pressed', b === el));
    $('#f-cuotas').value = el.dataset.k;
    calcular();
  },
  'tarjeta-desde-mov'() {
    const previo = borradorMov(), editando = hojaAct.editando;
    hojaTarjeta(null, async id => { await hojaMov('egreso', editando, Object.assign(previo, { pago: id })); toast('Tarjeta agregada'); });
  },
  'nueva-tarjeta': () => hojaTarjeta(null),
  mas: () => hojaMas(),
  frecuente: el => { const f = S.frecuentes[+el.dataset.i]; hojaMov('egreso', null, { monto: f.monto, cat: f.cat, descr: f.descr }); },
  'frecuente-hoja'(el) {
    const f = S.frecuentes[+el.dataset.i];
    $('#f-monto').value = fmtMonto(f.monto);
    $('#f-desc').value = f.descr;
    document.querySelectorAll('#capa .cats button').forEach(b => b.setAttribute('aria-pressed', b.dataset.k === f.cat));
    el.parentElement.querySelectorAll('button').forEach(b => b.classList.toggle('elegido', b === el));
    calcular();
  },
  async cobrar(el) {
    const r = await api('GET', '/api/resumen');
    S.resumen = r;
    const x = r.ingresos.find(i => i.id === +el.dataset.id);
    if (!x) return;
    if (x.cobrado) { await api('DELETE', '/api/ingresos/' + x.id + '/cobrar'); toast(x.nombre + ': sin cobrar'); refrescar(); }
    else hojaCobrar(x);
  },
  'sug-tarjeta': el => { $('#f-nombre').value = el.dataset.n; $('#f-cierre').focus(); },
  'editar-tarjeta': el => hojaTarjeta((S.tarjetas || []).find(t => t.id === +el.dataset.id)),
  async 'editar-cuota'(el) {
    const r = await api('GET', '/api/movs');
    S.movs = r.items;
    hojaMov(null, r.items.find(m => m.id === +el.dataset.id));
  },
  async 'pagar-tarjeta'(el) {
    const ts = await asegurarTarjetas(true);
    const t = ts.find(x => x.id === +el.dataset.id);
    if (!t) return;
    if (t.pagado) { await api('DELETE', '/api/tarjetas/' + t.id + '/pagar'); toast('Tarjeta ' + t.nombre + ': sin pagar'); refrescar(); }
    else hojaPagarTarjeta(t);
  },
  cat: el => el.parentElement.querySelectorAll('button').forEach(b => b.setAttribute('aria-pressed', b === el)),
  'fb-tipo': el => el.parentElement.querySelectorAll('button').forEach(b => b.setAttribute('aria-pressed', b === el)),
  velo: (el, e) => { if (e.target === el) cerrarHoja(); },
  cerrar: () => { const v = hojaAct && hojaAct.volver; cerrarHoja(); if (v) $('#capa').innerHTML = v; },
  'cerrar-festejo': () => { $('#capa').innerHTML = ''; },
  'ir-logros': () => { $('#capa').innerHTML = ''; location.hash = '#logros'; },
  recargar: () => ruta(),
  async demo() { await api('POST', '/api/demo-login'); await cargarMe(); location.hash = '#inicio'; ruta(); },
  async 'crear-cuenta'() { await api('POST', '/api/logout'); S.me = null; location.hash = '#registro'; ruta(); },
  async salir() { await api('POST', '/api/logout'); S.me = null; vistaActual = null; location.hash = ''; ruta(); },
  terminos: () => hojaTerminos(),
  'ob-sig': () => obAvanzar(1), 'ob-atras': () => obAvanzar(-1), 'ob-fin': () => obTerminar(),
  'nuevo-fijo': () => hojaFijo(null),
  'nuevo-ingreso': () => hojaIngreso(null),
  'sug-fijo': el => { const s = SUG_FIJOS.find(x => x.n === el.dataset.n); hojaFijo({ nombre: s.n, cat: s.c }, s); },
  'sug-ing': el => hojaIngreso({ nombre: el.dataset.n }),
  async 'editar-fijo'(el) { const r = S.resumen || await api('GET', '/api/resumen'); hojaFijo(r.fijos.find(f => f.id === +el.dataset.id)); },
  async 'editar-ingreso'(el) { const r = S.resumen || await api('GET', '/api/resumen'); hojaIngreso(r.ingresos.find(f => f.id === +el.dataset.id)); },
  'editar-mov': el => hojaMov(null, (S.movs || []).find(m => m.id === +el.dataset.id)),
  async pagar(el) {
    const r = await api('GET', '/api/resumen');
    S.resumen = r;
    const f = r.fijos.find(x => x.id === +el.dataset.id);
    if (!f) return;
    if (f.pagado) { await api('DELETE', '/api/fijos/' + f.id + '/pagar'); toast(f.nombre + ': sin pagar'); refrescar(); }
    else hojaPagar(f);
  },
  async checkin() { const r = await api('POST', '/api/checkin'); despuesDeGuardar(['¡Bien! Día anotado', r]); },
  'mov-mes': el => { S.movMes = el.dataset.k; mostrar('movimientos'); },
  'mov-tipo': el => { S.movTipo = el.dataset.k; mostrar('movimientos'); },
  instalar: () => hojaInstalar(),
  'no-instalar': () => { guardarLocal('sin-banner-instalar', true); refrescar(); },
  async 'instalar-ya'() { if (instalarAndroid) { instalarAndroid.prompt(); await instalarAndroid.userChoice; instalarAndroid = null; cerrarHoja(); } },
  async 'copiar-link'(el) {
    const input = el.parentElement.querySelector('input');
    try { await navigator.clipboard.writeText(input.value); toast('Link copiado'); } catch (e) { input.select(); toast('Seleccionado: copialo con el menú'); }
  },
  'activar-avisos': () => activarAvisos(),
  async 'probar-aviso'() { const r = await api('POST', '/api/push/test'); toast(r.sent ? 'Te mandamos un aviso de prueba' : 'No llegó: probá activar de nuevo'); },
  async pref(el) {
    await api('PUT', '/api/me', { [el.dataset.k]: el.checked });
    if (el.dataset.k === 'grande') { S.me.grande = el.checked; document.documentElement.classList.toggle('grande', el.checked); }
    toast('Guardado');
  },
  feedback: () => hojaFeedback(),
  'cambiar-pass': () => hojaPassword(),
  'borrar-cuenta': () => hojaBorrarCuenta(),
  async suscribir(el) {
    el.disabled = true; el.textContent = 'Abriendo Mercado Pago…';
    try { const r = await api('POST', '/api/cuenta/suscribir'); location.href = r.url; }
    catch (e) { toast(e.message); el.disabled = false; el.textContent = 'Suscribirme con Mercado Pago'; }
  },
  async 'cancelar-sus'(el) {
    if (el.dataset.ok !== '1') { el.dataset.ok = '1'; el.textContent = 'Tocá de nuevo para confirmar la baja'; return; }
    await api('POST', '/api/cuenta/cancelar'); toast('Suscripción dada de baja'); refrescar();
  },
  async borrar(el) {
    if (el.dataset.ok !== '1') { el.dataset.ok = '1'; el.textContent = 'Sí, borrar'; el.className = 'btn peligro'; return; }
    await hojaAct.enviar.borrar();
    despuesDeGuardar(['Borrado']);
  },
  async 'adm-pago'(el) { const r = await api('POST', '/api/admin/users/' + el.dataset.id + '/pago', { meses: 1 }); toast('Pago registrado hasta el ' + fechaCorta(r.hasta)); refrescar(); },
  async 'adm-prueba'(el) { await api('POST', '/api/admin/users/' + el.dataset.id + '/prueba', { dias: 7 }); toast('Prueba extendida 7 días'); refrescar(); },
  async 'adm-reset'(el) {
    const r = await api('POST', '/api/admin/reset-link', { email: el.dataset.mail });
    hoja('Link para elegir contraseña', '<p>Mandale este link a la persona (vale ' + r.horas + ' horas):</p><div class="acciones"><input readonly value="' + esc(r.link) + '" style="flex:1 1 200px;font:inherit;padding:12px;border-radius:12px;border:2px solid var(--line);background:var(--surface);color:var(--ink)"><button type="button" class="btn sec" data-acc="copiar-link">Copiar</button></div>', {});
  },
  async 'adm-visto'(el) { await api('PUT', '/api/admin/feedback/' + el.dataset.id, { seen: true }); refrescar(); }
};

FORMS.hoja = async f => despuesDeGuardar(await hojaAct.enviar.guardar());
FORMS.rapido = async f => {
  const txt = f.querySelector('#rapido').value.trim();
  if (!txt) return hojaMov('egreso');
  const x = interpretar(txt);
  await hojaMov('egreso', null, { monto: x.monto, cat: x.cat || 'otros', descr: x.descr });
  if (!x.monto) { const e = $('#capa .error'); e.textContent = 'No encontré el monto: escribilo acá arriba.'; e.hidden = false; }
};
FORMS.meta = async f => { const r = await api('PUT', '/api/me', { meta_ahorro: leerMonto(f.querySelector('#aj-meta').value) || null }); toast('Meta guardada'); if (r.logros && r.logros.length) festejar(r.logros); };
FORMS.nombre = async f => { await api('PUT', '/api/me', { name: f.querySelector('#aj-nombre').value }); toast('Nombre guardado'); await cargarMe(); };
FORMS['admin-settings'] = async f => {
  const v = id => { const el = f.querySelector(id); return el ? el.value : undefined; };
  await api('PUT', '/api/admin/settings', { precio_mensual: leerMonto(v('#ad-precio')), dias_prueba: leerMonto(v('#ad-dias')), mp_link: v('#ad-link'),
    alias_transferencia: v('#ad-alias'), contact_email: v('#ad-mail') });
  toast('Guardado');
};

document.addEventListener('click', async e => {
  const el = e.target.closest('[data-acc]');
  if (!el) return;
  const acc = ACC[el.dataset.acc];
  if (!acc) return;
  if (el.tagName === 'A' && el.dataset.acc === 'cerrar') { cerrarHoja(); return; }
  // los fondos oscuros solo cierran si se toca el fondo mismo (no lo que hay adentro)
  if ((el.dataset.acc === 'velo' || el.classList.contains('festejo')) && e.target !== el) return;
  if (el.type !== 'checkbox') e.preventDefault();
  try { await acc(el, e); } catch (err) {
    const p = $('#capa .error');
    if (p) { p.textContent = err.message; p.hidden = false; } else toast(err.message);
  }
});

document.addEventListener('change', e => {
  if (e.target.id === 'aj-hora') api('PUT', '/api/me', { notify_hour: +e.target.value }).then(() => toast('Hora guardada')).catch(err => toast(err.message));
});

document.addEventListener('submit', async e => {
  const f = e.target.closest('form[data-form]');
  if (!f) return;
  e.preventDefault();
  const btn = f.querySelector('[type=submit]'), err = f.querySelector('.error');
  if (err) err.hidden = true;
  if (btn) btn.disabled = true;
  try { await FORMS[f.dataset.form](f); } catch (x) {
    if (err) { err.textContent = x.message; err.hidden = false; } else toast(x.message);
  } finally { if (btn && document.body.contains(btn)) btn.disabled = false; }
});

document.addEventListener('input', e => {
  if (e.target.id === 'f-monto' || e.target.id === 'aj-meta') {
    const dig = e.target.value.replace(/\D/g, '').slice(0, 11);
    e.target.value = dig ? Number(dig).toLocaleString('es-AR') : '';
  }
  if (e.target.closest && e.target.closest('#capa')) {
    if (e.target.id === 'f-cuotas') document.querySelectorAll('#capa [data-acc=cuotas]').forEach(b => b.setAttribute('aria-pressed', b.dataset.k === e.target.value));
    calcular();
  }
});
document.addEventListener('keydown', e => { if (e.key === 'Escape' && hojaAct) cerrarHoja(); });

window.addEventListener('hashchange', ruta);
// al volver a la app (por ejemplo desde una notificación), refrescar
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible' && S.me && vistaActual) refrescar(); });

if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => {});

(async () => {
  try { await cargarMe(); } catch (e) { S.me = null; }
  ruta();
})();
