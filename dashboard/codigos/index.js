// SmartPark 2.0 - dashboard
// tudo que aparece na tela vem do broker (topicos em docs/topicos.md)

// broker e prefixo (da pra trocar pela URL com ?broker= e ?prefixo=)
const params = new URLSearchParams(location.search);
const BROKER = params.get('broker') || 'wss://broker.hivemq.com:8884/mqtt';
const PREFIXO = (params.get('prefixo') || 'cscf/equipe03').replace(/\/+$/, '');
// id aleatorio pra duas abas abertas nao derrubarem uma a outra
const CLIENT_ID = 'smartpark-dash-' + Math.random().toString(16).slice(2, 10);
const VALOR_AVULSO = 7.0;

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const hora = (t) => new Date(t).toLocaleTimeString('pt-BR', { hour12: false });
const reais = (v) => 'R$ ' + Number(v ?? 0).toFixed(2).replace('.', ',');
const NOME_TIPO = { comum: 'Comum', idoso: 'Idoso', pcd: 'PcD' };
const NOME_CPS = { cps1: 'CPS1', cps2: 'CPS2', cps3: 'CPS3', dash: 'Dashboard' };

// estado da tela, atualizado quando chega mensagem
const S = {
  conn: 'conectando',
  status: { cps1: null, cps2: null, cps3: null },
  s1: null, e1: null, e2: null, e3: null,       // cps1/sensor, cps1/estado, cps2/estado, cps3/estado
  alarmes: { cancela_travada: false, evasao: 0, vaga_irregular: '' },
  ajudaPedida: false,
  presenca: false,
  historico: [],                                  // pro grafico
  feed: [], log: [],
  brilhoModo: 'auto',                             // ultimo brilho escolhido aqui
  pagamento: null,                                // {placa, estado: enviando|ok|erro|sem_resposta, motivo}
};

// icones em svg
const IC = {
  check: '<path d="M20 6 9 17l-5-5"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  alert: '<path d="m21.7 18-8-14a2 2 0 0 0-3.5 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3"/><path d="M12 9v4M12 17h.01"/>',
  car: '<path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9l-1.4 2.9A3.7 3.7 0 0 0 2 12v4c0 .6.4 1 1 1h2"/><circle cx="7" cy="17" r="2"/><path d="M9 17h6"/><circle cx="17" cy="17" r="2"/>',
  info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
  wifiOff: '<path d="M12 20h.01M8.5 16.4a5 5 0 0 1 7 0M2 8.8a15 15 0 0 1 4.2-2.6M22 8.8a15 15 0 0 0-11.3-3.8M5 12.9a10 10 0 0 1 5.2-2.7M19 12.9a10 10 0 0 0-2.2-1.7M2 2l20 20"/>',
  headset: '<path d="M3 11h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-5Zm0 0a9 9 0 1 1 18 0m0 0v5a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3Z"/>',
  arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  card: '<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20"/>',
  gate: '<path d="M4 21V7"/><path d="M4 9l14-6"/><path d="M2 21h6"/>',
  siren: '<path d="M7 18v-6a5 5 0 1 1 10 0v6"/><path d="M5 21a1 1 0 0 1-1-1v-1a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v1a1 1 0 0 1-1 1z"/><path d="M12 2v1M21 7l-1 .5M3 7l1 .5"/>',
  wrench: '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.8-3.8a6 6 0 0 1-7.9 7.9l-6.9 6.9a2.1 2.1 0 0 1-3-3l6.9-6.9a6 6 0 0 1 7.9-7.9z"/>',
};
const icon = (n, cls = 'i') => `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true">${IC[n]}</svg>`;

// display de 7 segmentos (usado no cartao e no totem 3D)
const SEGMENTOS = { '0': 'abcdef', '1': 'bc', '2': 'abdeg', '3': 'abcdg', '4': 'bcfg', '5': 'acdfg', '6': 'acdefg', '7': 'abc', '8': 'abcdefg', '9': 'abcdfg', '-': 'g', ' ': '' };
function textoDisplay(valor) {
  if (valor === null || valor === undefined || valor === '----') return '----';
  return String(Math.max(0, Math.min(9999, Number(valor) || 0))).padStart(4, ' ');  // alinha na direita igual o TM1637
}
function desenharDisplay(ctx, texto, W, H, forte = true) {
  ctx.fillStyle = '#07090d'; ctx.fillRect(0, 0, W, H);
  const n = 4, pad = W * 0.06, gap = W * 0.04;
  const dw = (W - 2 * pad - gap * (n - 1)) / n, dh = H * 0.72, t = dw * 0.17, g = t * 0.14;
  const ligado = forte ? '#ff3b30' : 'rgba(255,59,48,.55)', apagado = 'rgba(255,59,48,.05)';
  const poly = (pts, cor) => { ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath(); ctx.fillStyle = cor; ctx.fill(); };
  const h = (x1, x2, y) => [[x1, y], [x1 + t / 2, y - t / 2], [x2 - t / 2, y - t / 2], [x2, y], [x2 - t / 2, y + t / 2], [x1 + t / 2, y + t / 2]];
  const v = (x, y1, y2) => [[x, y1], [x + t / 2, y1 + t / 2], [x + t / 2, y2 - t / 2], [x, y2], [x - t / 2, y2 - t / 2], [x - t / 2, y1 + t / 2]];
  for (let i = 0; i < n; i++) {
    const x0 = pad + i * (dw + gap), y0 = (H - dh) / 2;
    const xL = x0 + t / 2, xR = x0 + dw - t / 2, yA = y0 + t / 2, yG = y0 + dh / 2, yD = y0 + dh - t / 2;
    const forma = {
      a: h(xL + g, xR - g, yA), g: h(xL + g, xR - g, yG), d: h(xL + g, xR - g, yD),
      f: v(xL, yA + g, yG - g), b: v(xR, yA + g, yG - g), e: v(xL, yG + g, yD - g), c: v(xR, yG + g, yD - g),
    };
    const acesos = SEGMENTOS[texto[i]] ?? '';
    for (const s of 'abcdefg') poly(forma[s], acesos.includes(s) ? ligado : apagado);
  }
}

// cores dos LEDs e da fita
const COR_LED = { verde: '#22c55e', vermelho: '#ef4444', amarelo: '#eab308', azul: '#3b82f6', laranja: '#f97316', branco: '#e5e7eb', apagado: '#1f2430' };
const COR_VAGA = { comum: '#16a34a', idoso: '#e5a500', pcd: '#2563eb', ocupada: '#dc2626', interditada: '#f97316', nd: '#475569' };

// quem publica e quem assina cada topico (pra animacao do 3D)
const ROTAS = {
  'cps1/sensor': ['cps1', ['cps2', 'cps3', 'dash']],
  'cps1/estado': ['cps1', ['dash']],
  'cps1/comando': ['dash', ['cps1']],
  'cps1/status': ['cps1', ['cps2', 'cps3', 'dash']],
  'cps2/sensor': ['cps2', ['dash']],
  'cps2/estado': ['cps2', ['cps1', 'cps3', 'dash']],
  'cps2/alarme': ['cps2', ['cps3', 'dash']],
  'cps2/comando': ['dash', ['cps2']],
  'cps2/status': ['cps2', ['dash']],
  'pagamento': ['dash', ['cps2']],
  'cps3/sensor': ['cps3', ['cps2', 'dash']],
  'cps3/estado': ['cps3', ['dash']],
  'cps3/comando': ['dash', ['cps3']],
  'cps3/status': ['cps3', ['dash']],
};

// MQTT
let client = null;
function conectar() {
  $('conn-meta').textContent = BROKER.replace(/^wss?:\/\//, '') + '  ' + PREFIXO;
  if (!window.mqtt) { S.conn = 'erro'; agendarRender(); return; }
  client = mqtt.connect(BROKER, {
    clientId: CLIENT_ID, clean: true, keepalive: 30,
    reconnectPeriod: 2000,        // reconecta sozinho a cada 2 s
    connectTimeout: 10000,
  });
  client.on('connect', () => {
    S.conn = 'conectado';
    client.subscribe(PREFIXO + '/#', { qos: 1 });
    agendarRender();
  });
  client.on('reconnect', () => { S.conn = 'reconectando'; agendarRender(); });
  client.on('close', () => { if (S.conn === 'conectado') S.conn = 'reconectando'; agendarRender(); });
  client.on('offline', () => { S.conn = 'offline'; agendarRender(); });
  client.on('error', (e) => console.warn('MQTT:', e.message));
  client.on('message', aoReceber);
}

// comandos vao com QoS 1 e sem retain
function publicar(sub, obj) {
  if (!client || !client.connected) { toast('Sem conexão com o broker. Tentando reconectar.', true); return false; }
  client.publish(PREFIXO + '/' + sub, JSON.stringify(obj), { qos: 1, retain: false }, (err) => {
    if (err) toast('Falha ao enviar para ' + sub, true);
  });
  toast(`Enviado para <code>${esc(sub)}</code>`);
  return true;
}

function aoReceber(topico, payload, packet) {
  const rel = topico.startsWith(PREFIXO + '/') ? topico.slice(PREFIXO.length + 1) : topico;
  const texto = new TextDecoder().decode(payload);
  const retido = !!packet.retain;
  registrarLog(rel, texto, retido);
  let d = null;
  if (texto.startsWith('{')) { try { d = limpar(JSON.parse(texto)); } catch { d = null; } }
  if (d && rel === 'cps1/sensor') d.vagas = (Array.isArray(d.vagas) ? d.vagas : []).filter((v) => v && typeof v === 'object');
  if (d && rel === 'cps2/estado' && !Array.isArray(d.placas)) d.placas = [];

  const st = rel.match(/^(cps[123])\/status$/);
  if (st) {
    const antes = S.status[st[1]];
    S.status[st[1]] = texto || null;
    if (!retido && antes !== texto && texto) feedStatus(st[1], texto);
  } else switch (rel) {
    case 'cps1/sensor':
      if (d && Array.isArray(d.vagas)) {
        if (!retido && S.s1) feedVagas(S.s1, d);
        S.s1 = d;
        S.historico.push({ t: Date.now(), livres: d.livres });
        if (S.historico.length > 80) S.historico.shift();
      } else if (!texto) S.s1 = null;     // retido apagado
      break;
    case 'cps1/estado': S.e1 = d; break;
    case 'cps2/estado':
      S.e2 = d;
      if (d) { S.alarmes.cancela_travada = !!d.travada; S.alarmes.evasao = d.evasao || 0; S.alarmes.vaga_irregular = d.vaga_irregular || ''; }
      break;
    case 'cps2/alarme':
      if (d) {
        if (d.tipo === 'evasao') S.alarmes.evasao = d.ativo ? (d.diferenca || 1) : 0;
        else if (d.tipo === 'cancela_travada') S.alarmes.cancela_travada = !!d.ativo;
        else if (d.tipo === 'vaga_irregular') S.alarmes.vaga_irregular = d.ativo ? (d.vaga || 'V4') : '';
        feedAlarme(d);
      }
      break;
    case 'cps2/sensor': if (d) { feedEvento(d); conferirPagamento(d); } break;
    case 'cps3/sensor':
      if (d && d.ajuda) { S.ajudaPedida = true; addFeed(['cps3', 'dash'], 'alerta', 'headset', 'Pedido de ajuda no totem', 'O motorista apertou o botão do CPS3; atenda pelo painel.'); }
      if (d && 'presenca' in d) S.presenca = !!d.presenca;
      break;
    case 'cps3/estado':
      S.e3 = d;
      if (d && d.ajuda !== 'aguardando') S.ajudaPedida = false;
      break;
    case 'cps1/comando': case 'cps2/comando': case 'cps3/comando': case 'pagamento':
      if (d && !retido) feedComando(rel, d);
      break;
  }
  if (!retido && gemeo) gemeo.pulso(rel);
  agendarRender();
}

// painel de interacao entre sistemas
function addFeed(fluxo, tom, ic, titulo, detalhe) {
  S.feed.unshift({ t: Date.now(), fluxo, tom, ic, titulo, detalhe });
  if (S.feed.length > 60) S.feed.pop();
  feedMudou = true;
}
const P = (placa) => `<span class="inline-plate">${esc(placa)}</span>`;

function feedVagas(antes, agora) {
  for (const v of agora.vagas) {
    const a = antes.vagas.find((x) => x.id === v.id);
    if (!a || a.ocupada === v.ocupada) continue;
    addFeed(['cps1', 'cps3'], 'info', 'car', `Vaga ${v.id} ${v.ocupada ? 'ocupada' : 'liberada'}`,
      `CPS1 mediu ${v.cm} cm e publicou ${agora.livres} livre(s); o totem atualiza o número e a fita.`);
  }
  if (agora.livres_comuns === 0 && antes.livres_comuns > 0)
    addFeed(['cps1', 'cps2', 'cps3'], 'alerta', 'alert', 'Sem vaga comum livre',
      'O CPS2 passa a negar placas comuns; o LED do totem fica vermelho quando não sobra vaga comum.');
}

function feedEvento(d) {
  const placa = d.placa ? P(d.placa) : '';
  switch (d.evento) {
    case 'entrada':
      addFeed(['cps1', 'cps2'], 'ok', 'check', `Havia vaga ${NOME_TIPO[d.tipo] || ''} no CPS1, CPS2 abriu para ${placa}`,
        d.avulso ? 'Placa sem cadastro: entrou como avulso e paga R$ 7,00 pelo celular antes de sair.' : `Placa cadastrada (${NOME_TIPO[d.tipo] || d.tipo}); débito automático na saída.`);
      break;
    case 'saida':
      addFeed(['cps2'], 'ok', 'check', `${placa} saiu`,
        d.valor ? `Débito automático de ${reais(d.valor)}; saldo ${reais(d.saldo)}.` : 'Avulso já pago pelo celular; saída liberada.');
      break;
    case 'negado': {
      const M = {
        lotado: [['cps1', 'cps2'], `CPS1 lotado, CPS2 negou ${placa}`, `Sem vaga ${NOME_TIPO[d.tipo] || ''} livre; o buzzer tocou.`],
        ja_dentro: [['cps2'], `CPS2 negou ${placa}`, 'Essa placa já está dentro.'],
        nao_registrado: [['cps2'], `CPS2 negou a saída de ${placa}`, 'Não há entrada registrada para essa placa.'],
        pagamento_pendente: [['cps2'], `CPS2 negou a saída de ${placa}`, 'Avulso sem pagamento: pague pelo celular para sair.'],
        sem_carro_na_cancela: [['dash', 'cps2'], `Câmera leu ${placa}, mas não há carro na cancela`, 'O HC-SR04 da cancela não vê carro; a leitura foi ignorada.'],
      };
      const [fl, t, det] = M[d.motivo] || [['cps2'], `CPS2 negou ${placa}`, d.motivo || ''];
      addFeed(fl, 'neg', 'x', t, det);
      break;
    }
    case 'pagamento':
      if (d.ok) addFeed(['dash', 'cps2'], 'ok', 'card', `Pagamento de ${placa} confirmado`, `Celular enviou ${reais(d.valor)}; o CPS2 libera a saída dessa placa.`);
      else addFeed(['dash', 'cps2'], 'neg', 'x', `Pagamento de ${placa} recusado`, 'Essa placa não está dentro como avulso.');
      break;
    case 'abertura_manual':
      addFeed(['dash', 'cps2'], 'info', 'gate', 'Operador abriu a cancela', 'Comando manual; fecha sozinha em 5 s.');
      break;
    case 'modo':
      if (d.modo === 'emergencia') addFeed(['dash', 'cps2', 'cps1', 'cps3'], 'alerta', 'siren', 'Emergência ativada',
        'CPS2 abre e mantém a cancela; CPS1 pisca os LEDs; CPS3 pisca a fita em branco.');
      else addFeed(['dash', 'cps2', 'cps1', 'cps3'], 'ok', 'check', 'Emergência encerrada', 'Cancela fecha e os LEDs voltam ao normal.');
      break;
    case 'livre':
      addFeed(['cps2'], 'info', 'gate', `${placa} passou livre`, 'Cancela aberta pela emergência.');
      break;
  }
}

function feedAlarme(d) {
  if (d.tipo === 'cancela_travada') {
    if (d.ativo) addFeed(['cps2', 'cps3'], 'neg', 'alert', 'Cancela travada aberta', 'O fim de curso não confirmou o fechamento; o totem pisca o LED vermelho.');
    else addFeed(['cps2', 'cps3'], 'ok', 'check', 'Cancela voltou a fechar', 'Fim de curso confirmou; alarme encerrado.');
  } else if (d.tipo === 'evasao') {
    if (d.ativo) addFeed(['cps1', 'cps2', 'cps3'], 'neg', 'alert', `Evasão: ${d.diferenca} carro(s) sem registro`, 'Há mais vagas ocupadas (CPS1) do que carros que entraram (CPS2).');
    else addFeed(['cps1', 'cps2'], 'ok', 'check', 'Evasão resolvida', 'Vagas ocupadas e carros dentro voltaram a bater.');
  } else if (d.tipo === 'vaga_irregular') {
    if (d.ativo) addFeed(['cps1', 'cps2', 'cps3'], 'neg', 'alert', `Vaga PcD ${esc(d.vaga)} ocupada sem credencial`, 'Nenhum carro PcD entrou pela cancela; o totem pisca a vaga. Avisar a fiscalização.');
    else addFeed(['cps1', 'cps2'], 'ok', 'check', 'Alarme da vaga PcD encerrado', 'A vaga PcD liberou, o carro PcD está dentro ou o CPS1 saiu do ar.');
  }
}

function feedComando(rel, d) {
  if ('ping' in d && Object.keys(d).length === 1) return;
  if (rel === 'cps1/comando' && d.manutencao)
    addFeed(['dash', 'cps1', 'cps3'], 'info', 'wrench', `Operador ${d.ativo === false ? 'liberou' : 'interditou'} a vaga ${esc(d.manutencao)}`,
      d.ativo === false ? 'A vaga volta para a contagem.' : 'O LED dela pisca, sai da contagem e fica laranja na fita do totem.');
  if (rel === 'cps2/comando' && d.placa)
    addFeed(['dash', 'cps2'], 'info', 'car', `Câmera simulada leu ${P(d.placa)}`, `Sentido ${d.sentido === 'saida' ? 'saída' : 'entrada'}; o CPS2 decide se abre.`);
  if (rel === 'cps3/comando' && d.ajuda === 'atendido')
    addFeed(['dash', 'cps3'], 'ok', 'headset', 'Operador atendeu o chamado', 'O CPS3 acende o LED azul por 10 s.');
  if (rel === 'cps3/comando' && d.brilho)
    addFeed(['dash', 'cps3'], 'info', 'info', `Brilho do totem: ${d.brilho}`, d.brilho === 'auto' ? 'Volta a seguir o PIR.' : 'Forçado pelo operador.');
  if (rel === 'pagamento')
    addFeed(['dash', 'cps2'], 'info', 'card', `Celular pagou ${P(d.placa)}`, `${reais(d.valor)} publicados em pagamento; aguardando o CPS2.`);
}

function feedStatus(cps, texto) {
  const nome = { cps1: 'CPS1 Vagas', cps2: 'CPS2 Cancela', cps3: 'CPS3 Totem' }[cps];
  if (texto === 'offline') {
    if (cps === 'cps1') addFeed(['cps1', 'cps3'], 'neg', 'wifiOff', 'CPS1 caiu (Last Will)', 'O broker publicou offline por ele; o totem mostra ---- e a fita pisca laranja.');
    else addFeed([cps], 'neg', 'wifiOff', `${nome} caiu (Last Will)`, 'O broker publicou offline em nome do ESP32.');
  } else if (texto === 'online') addFeed([cps], 'ok', 'check', `${nome} online`, 'Reconectou e refez as assinaturas.');
}

// log MQTT
function registrarLog(rel, texto, retido) {
  S.log.unshift({ t: Date.now(), rel, texto, retido });
  if (S.log.length > 100) S.log.pop();
  logMudou = true;
}

// pagamento pelo celular
const normPlaca = (s) => String(s || '').toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 7);
const avulsosPendentes = () => (S.e2?.placas || []).filter((p) => p.avulso && !p.pago);
let pagTimer = null;
function pagar() {
  const placa = normPlaca($('p-placa').value);
  const msg = $('p-msg');
  if (!placa) { msg.className = 'pay-msg erro'; msg.textContent = 'Escolha ou digite a placa do seu carro.'; return; }
  if (!avulsosPendentes().some((p) => p.placa === placa)) {
    msg.className = 'pay-msg erro';
    msg.textContent = `${placa} não está dentro como avulso aguardando pagamento.`;
    return;
  }
  if (!publicar('pagamento', { placa, valor: VALOR_AVULSO })) return;
  S.pagamento = { placa, estado: 'enviando' };
  clearTimeout(pagTimer);
  pagTimer = setTimeout(() => { if (S.pagamento?.estado === 'enviando') { S.pagamento.estado = 'sem_resposta'; agendarRender(); } }, 12000);
  agendarRender();
}
function conferirPagamento(d) {
  if (d.evento !== 'pagamento' || !S.pagamento || d.placa !== S.pagamento.placa) return;
  S.pagamento.estado = d.ok ? 'ok' : 'erro';
  S.pagamento.motivo = d.motivo;
}

// desenha a pagina
let pendente = false, feedMudou = true, logMudou = true;
function agendarRender() {
  if (pendente) return;
  pendente = true;
  requestAnimationFrame(() => {
    pendente = false;
    // guarda o foco porque os botoes sao redesenhados
    const k = document.activeElement?.dataset?.k;
    render();
    if (k) document.querySelector(`[data-k="${CSS.escape(k)}"]`)?.focus();
  });
}

// o broker e publico, entao escapa o HTML de tudo que chega antes de mostrar
function limpar(v) {
  if (typeof v === 'string') return v.replace(/[<>&"'`]/g, '');
  if (Array.isArray(v)) return v.map(limpar);
  if (v && typeof v === 'object') {
    const o = {};
    for (const k of Object.keys(v)) o[k] = limpar(v[k]);
    return o;
  }
  return v;
}

// se uma parte der erro as outras continuam desenhando
function seguro(fn) {
  try { fn(); } catch (e) { console.warn('render', fn.name, e); }
}

function render() {
  seguro(renderTopo);
  seguro(renderKpis);
  seguro(renderCps1);
  seguro(renderCps2);
  seguro(renderCps3);
  seguro(renderAlarmes);
  if (feedMudou) { seguro(renderFeed); feedMudou = false; }
  if (logMudou) { seguro(renderLog); logMudou = false; }
  seguro(renderPagar);
  if (gemeo) seguro(() => gemeo.atualizar(S));
  if (mapaMarcador) seguro(atualizarMapa);
  document.body.classList.toggle('desconectado', S.conn !== 'conectado');
  document.querySelectorAll('[data-acao], #cam-form button, #p-pagar').forEach((b) => { b.disabled = S.conn !== 'conectado' || b.dataset.off === '1'; });
}

const TXT_STATUS = (st) => st === 'online' ? 'online' : st === 'offline' ? 'offline' : 'sem dado';
function renderTopo() {
  for (const c of ['cps1', 'cps2', 'cps3']) {
    const st = S.status[c] || 'nd';
    const pill = $('pill-' + c); pill.dataset.state = st; pill.querySelector('.pill-st span').textContent = TXT_STATUS(st);
    const sd = $('st-' + c); sd.dataset.state = st; sd.querySelector('span').textContent = TXT_STATUS(st);
  }
  const conn = $('conn'); conn.dataset.state = S.conn;
  $('conn-txt').textContent = { conectando: 'Conectando', conectado: 'Conectado', reconectando: 'Reconectando', offline: 'Sem conexão', erro: 'MQTT.js não carregou' }[S.conn];
}

function renderKpis() {
  const s1 = S.s1;
  $('k-livres').innerHTML = s1 ? `${s1.livres}<small>de ${s1.total}</small>` : '–<small>aguardando CPS1</small>';
  $('k-tipos').innerHTML = s1 ? ['comum', 'idoso', 'pcd'].map((t) => `<span class="tchip"><i class="sw sw-${t}"></i>${NOME_TIPO[t]} <b>${s1.livres_tipo?.[t] ?? 0}</b></span>`).join('') : '';
  renderSpark();
  const e2 = S.e2;
  $('k-dentro').textContent = e2 ? e2.dentro : '–';
  const pend = avulsosPendentes().length;
  $('k-dentro-s').textContent = e2 ? (pend ? `${pend} avulso(s) sem pagar` : 'nenhum avulso pendente') : 'aguardando CPS2';
  $('k-cancela').textContent = e2 ? (e2.cancela === 'aberta' ? 'Aberta' : 'Fechada') : '–';
  $('k-cancela-s').textContent = e2 ? (e2.modo === 'emergencia' ? 'modo emergência' : 'modo normal') : 'aguardando CPS2';
  const n = listaAlarmes().length;
  $('k-alarmes').textContent = n;
  $('k-alarmes-s').textContent = n ? 'veja o painel ao lado' : 'tudo em ordem';
}

// grafico das vagas livres
function renderSpark() {
  const svg = $('spark-svg'), H = S.historico, box = $('spark');
  const W = box.clientWidth || 300, Ht = box.clientHeight || 64;
  svg.setAttribute('viewBox', `0 0 ${W} ${Ht}`);
  const total = S.s1?.total || 4;
  if (H.length < 2) { svg.innerHTML = `<line x1="0" x2="${W}" y1="${Ht - 1}" y2="${Ht - 1}" stroke="#e3e6eb"/>`; $('spark-cap').textContent = 'Histórico desta sessão'; return; }
  const t0 = H[0].t, t1 = Math.max(H[H.length - 1].t, t0 + 1);
  const x = (t) => ((t - t0) / (t1 - t0)) * (W - 4) + 2;
  const y = (v) => Ht - 4 - (v / total) * (Ht - 10);
  let d = `M${x(H[0].t)},${y(H[0].livres)}`;
  for (let i = 1; i < H.length; i++) d += `H${x(H[i].t)}V${y(H[i].livres)}`;
  const grade = [0, total].map((v) => `<line x1="0" x2="${W}" y1="${y(v)}" y2="${y(v)}" stroke="#eef0f3"/>`).join('');
  const last = H[H.length - 1];
  svg.innerHTML = `${grade}<path d="${d}" fill="none" stroke="var(--cps1)" stroke-width="2" stroke-linejoin="round"/>
    <circle cx="${x(last.t)}" cy="${y(last.livres)}" r="4" fill="var(--cps1)" stroke="#fff" stroke-width="2"/>
    <line id="spark-x" x1="0" x2="0" y1="0" y2="${Ht}" stroke="#9aa1ad" stroke-dasharray="2 2" opacity="0"/>`;
  const min = Math.round((t1 - t0) / 60000);
  $('spark-cap').textContent = `Vagas livres nos últimos ${min < 1 ? 'segundos' : min + ' min'}`;
}
function sparkHover(ev) {
  const H = S.historico, box = $('spark');
  if (H.length < 2) return;
  const r = box.getBoundingClientRect(), W = r.width;
  const t0 = H[0].t, t1 = Math.max(H[H.length - 1].t, t0 + 1);
  const tAlvo = t0 + ((ev.clientX - r.left - 2) / (W - 4)) * (t1 - t0);
  let p = H[0]; for (const h of H) if (h.t <= tAlvo) p = h;
  const px = ((p.t - t0) / (t1 - t0)) * (W - 4) + 2;
  box.classList.add('hover');
  const tip = $('spark-tip'); tip.style.left = px + 'px'; tip.textContent = `${hora(p.t)}  ${p.livres} livre(s)`;
  const l = $('spark-x'); if (l) { l.setAttribute('x1', px); l.setAttribute('x2', px); l.setAttribute('opacity', '1'); }
}

function renderCps1() {
  const s1 = S.s1;
  if (!s1) return;
  const leds = S.e1?.leds || [];
  $('bays').innerHTML = s1.vagas.map((v, i) => {
    const estado = v.interditada ? 'interditada' : v.ocupada ? 'ocupada' : 'livre';
    const led = leds[i] || (v.ocupada ? 'vermelho' : 'verde');
    const rot = { livre: 'Livre', ocupada: 'Ocupada', interditada: 'Interditada' }[estado];
    return `<div class="bay t-${esc(v.tipo)} ${estado}" data-vaga="${esc(v.id)}" data-estado="${estado}">
      <div class="bay-id">${esc(v.id)} <span class="bay-tipo">${NOME_TIPO[v.tipo] || esc(v.tipo)}</span></div>
      <button class="btn btn-sm" data-acao="manutencao" data-vaga="${esc(v.id)}" data-ativo="${!v.interditada}" data-k="int-${esc(v.id)}">${v.interditada ? 'Liberar' : 'Interditar'}</button>
      <div class="bay-st">${v.ocupada && !v.interditada ? icon('car') : ''}${rot}</div>
      <div class="bay-meta"><span title="LED da vaga: ${esc(led)}" class="led ${esc(led)}"></span><span>LED ${esc(led)}</span><span>${v.cm >= 399 ? 'sem eco' : esc(v.cm) + ' cm'}</span></div>
    </div>`;
  }).join('');
}

function renderCps2() {
  const e2 = S.e2;
  const fact = (dt, dd) => `<div class="fact"><dt>${dt}</dt><dd>${dd}</dd></div>`;
  const svg = $('gate-svg');
  if (!e2) { $('cps2-facts').innerHTML = fact('Estado', 'aguardando'); return; }
  const aberta = e2.cancela === 'aberta';
  svg.dataset.aberta = aberta; svg.setAttribute('aria-label', 'Cancela ' + (aberta ? 'aberta' : 'fechada'));
  $('gate-light').setAttribute('fill', aberta ? '#16a34a' : '#dc2626');
  $('cps2-facts').innerHTML = [
    fact('Cancela', aberta ? 'Aberta' : 'Fechada'),
    fact('Fim de curso', e2.fim_curso === 'aberta' ? 'Aberta' : 'Fechada'),
    fact('Modo', e2.modo === 'emergencia' ? 'Emergência' : 'Normal'),
    fact('Carro', e2.carro ? 'Na cancela' : 'Não'),
    fact('Sentido', e2.sentido === 'saida' ? 'Saída' : 'Entrada'),
    fact('Dentro', e2.dentro),
  ].join('');
  const flags = [];
  flags.push(e2.travada ? `<span class="flag on-critical">${icon('alert')}Travada</span>` : `<span class="flag">${icon('check')}Não travada</span>`);
  flags.push(e2.evasao > 0 ? `<span class="flag on-serious">${icon('alert')}Evasão ${e2.evasao}</span>` : `<span class="flag">${icon('check')}Sem evasão</span>`);
  if (e2.vagas_ok === false) flags.push(`<span class="flag on-serious">${icon('alert')}Sem dado de vagas (CPS1 fora)</span>`);
  if (e2.vaga_irregular) flags.push(`<span class="flag on-serious">${icon('alert')}PcD irregular ${esc(e2.vaga_irregular)}</span>`);
  if (e2.modo === 'emergencia') flags.push(`<span class="flag on-critical">${icon('siren')}Emergência</span>`);
  $('cps2-flags').innerHTML = flags.join('');
  const placas = e2.placas || [];
  $('plates').innerHTML = placas.length ? placas.map((p) => `<span class="plate-wrap"><span class="plate"><b>${esc(p.placa)}</b></span>
      <span class="plate-tag ${p.avulso && !p.pago ? 'pend' : ''}">${p.avulso ? (p.pago ? 'avulso, pago' : 'avulso, a pagar') : 'cadastrada, ' + (NOME_TIPO[p.tipo] || p.tipo)}</span></span>`).join('')
    : '<span class="empty">Nenhum carro dentro</span>';
  const em = e2.modo === 'emergencia';
  const b = $('btn-emerg'); b.setAttribute('aria-pressed', em); b.querySelector('span').textContent = em ? 'Encerrar emergência' : 'Emergência';
}

const ajudaPendente = () => S.e3?.ajuda === 'aguardando' || S.ajudaPedida;
let ultimoDisplay = '';
function renderCps3() {
  const e3 = S.e3;
  const txt = textoDisplay(e3 ? e3.display : null);
  const forte = e3?.brilho !== 'baixo';
  const chave = txt + forte;
  if (chave !== ultimoDisplay) {
    const cv = $('seg7'); desenharDisplay(cv.getContext('2d'), txt, cv.width, cv.height, forte);
    cv.setAttribute('aria-label', 'Display: ' + txt.trim()); ultimoDisplay = chave;
  }
  $('t-led').className = 'tled ' + (e3?.led || '');
  $('t-azul').className = 'tled ' + (e3?.ajuda === 'atendida' ? 'azul' : ajudaPendente() ? 'azul-pisca' : '');
  const strip = $('t-strip'); strip.classList.toggle('pisca', !!e3?.fita_pisca);
  strip.setAttribute('aria-label', 'Fita NeoPixel: ' + ((e3?.fita || []).join(', ') || 'sem dado') + (e3?.fita_pisca ? ', piscando' : ''));
  const fita = e3?.fita || [];
  strip.querySelectorAll('.px').forEach((px, i) => {
    const c = COR_LED[fita[i]] || COR_LED.apagado;
    px.style.background = c; px.style.boxShadow = fita[i] && fita[i] !== 'apagado' ? `0 0 10px ${c}` : 'none';
    px.classList.toggle('pisca', e3?.pisca_vaga === i);
  });
  const fact = (dt, dd) => `<div class="fact"><dt>${dt}</dt><dd>${dd}</dd></div>`;
  $('cps3-facts').innerHTML = e3 ? [
    fact('Display', esc(String(e3.display))),
    fact('Brilho', e3.brilho === 'alto' ? 'Alto' : 'Baixo'),
    fact('Presença (PIR)', e3.presenca ? 'Sim' : 'Não'),
  ].join('') : fact('Estado', 'aguardando');
  const box = $('ajuda-box'), pend = ajudaPendente();
  box.classList.toggle('pendente', pend);
  $('ajuda-txt').innerHTML = pend ? 'Chamado aberto<small>Motorista no totem pediu ajuda</small>'
    : e3?.ajuda === 'atendida' ? 'Chamado atendido<small>LED azul aceso por 10 s</small>' : 'Sem chamado<small>Botão de ajuda do totem</small>';
  const btn = $('btn-atender'); btn.dataset.off = pend ? '0' : '1'; btn.classList.toggle('btn-primary', pend);
  document.querySelectorAll('#seg-brilho button').forEach((b) => b.setAttribute('aria-pressed', b.dataset.v === (e3?.brilho_forcado || S.brilhoModo)));
}

function listaAlarmes() {
  const L = [];
  if (S.alarmes.cancela_travada) L.push({ tom: 'critical', ic: 'alert', t: 'Cancela travada aberta', d: 'Mandou fechar e o fim de curso continua aberto há mais de 3 s.' });
  if (S.alarmes.evasao > 0) L.push({ tom: 'serious', ic: 'alert', t: `Evasão: ${S.alarmes.evasao} carro(s) sem registro`, d: 'Vagas ocupadas no CPS1 > carros que entraram pelo CPS2.' });
  if (S.alarmes.vaga_irregular) L.push({ tom: 'serious', ic: 'alert', t: `Vaga PcD ${esc(S.alarmes.vaga_irregular)} ocupada sem credencial`, d: 'Nenhum carro PcD entrou pela cancela. Avisar a fiscalização.' });
  if (ajudaPendente()) L.push({ tom: 'warning', ic: 'headset', t: 'Pedido de ajuda no totem', d: 'Botão do CPS3 apertado.', acao: 'atender' });
  if (S.e2?.modo === 'emergencia') L.push({ tom: 'serious', ic: 'siren', t: 'Modo emergência ativo', d: 'Cancela aberta; LEDs das vagas e fita piscando.' });
  for (const c of ['cps1', 'cps2', 'cps3']) if (S.status[c] === 'offline')
    L.push({ tom: 'warning', ic: 'wifiOff', t: `${NOME_CPS[c]} offline`, d: c === 'cps1' ? 'Last Will publicado; o totem mostra ----.' : 'Last Will publicado pelo broker.' });
  return L;
}
function renderAlarmes() {
  const L = listaAlarmes();
  $('alarmes-sub').textContent = L.length ? `${L.length} ativo(s)` : '';
  const html = L.length ? L.map((a) => `<li class="alarm ${a.tom}">${icon(a.ic)}<div><div class="t">${a.t}</div><div class="d">${a.d}</div></div>
      ${a.acao ? `<button class="btn btn-sm btn-primary" data-acao="atender" data-k="al-atender">Atender</button>` : '<span></span>'}</li>`).join('')
    : `<li class="alarm-ok">${icon('check')}Nenhum alarme ativo</li>`;
  const ul = $('alarm-list');
  if (ul.dataset.html !== html) { ul.innerHTML = html; ul.dataset.html = html; }
}

function renderFeed() {
  if (!S.feed.length) return;
  $('feed').innerHTML = S.feed.map((e) => `<li class="ev ${e.tom}">
    <div class="ev-ic">${icon(e.ic)}</div>
    <div><p class="ev-t">${e.titulo}</p><p class="ev-d">${e.detalhe}</p>
      <div class="flow" role="group" aria-label="Sistemas envolvidos">${e.fluxo.map((c) => `<span class="sys c-${c}">${NOME_CPS[c]}</span>`).join(icon('arrow'))}</div></div>
    <time>${hora(e.t)}</time></li>`).join('');
  $('feed-sub').textContent = `${S.feed.length} evento(s)`;
}

function renderLog() {
  const f = $('log-filtro').value.trim().toLowerCase(), sys = $('log-sys').value;
  const linhas = S.log.filter((m) => (!sys || m.rel.startsWith(sys)) && (!f || (m.rel + ' ' + m.texto).toLowerCase().includes(f)));
  $('log-body').innerHTML = linhas.map((m) => `<tr><td>${hora(m.t)}</td><td class="tp">${esc(m.rel)}</td><td>${m.retido ? '<span class="rbadge" title="mensagem retida">R</span>' : ''}</td><td title="${esc(m.texto)}">${esc(m.texto || '(vazio)')}</td></tr>`).join('');
  $('log-sub').textContent = `${linhas.length} de ${S.log.length}`;
}

function renderPagar() {
  const s1 = S.s1;
  $('p-livres').textContent = s1 ? s1.livres : '–';
  $('p-tipos').innerHTML = s1 ? ['comum', 'idoso', 'pcd'].map((t) => `<span class="tchip"><i class="sw sw-${t}"></i>${NOME_TIPO[t]} <b>${s1.livres_tipo?.[t] ?? 0}</b></span>`).join('') : '<span class="tchip">aguardando CPS1</span>';
  const atual = normPlaca($('p-placa').value);
  const lista = avulsosPendentes();
  const html = lista.length ? lista.map((p) => `<button data-placa="${esc(p.placa)}" aria-pressed="${p.placa === atual}" data-k="pp-${esc(p.placa)}" aria-label="Escolher ${esc(p.placa)}"><span class="plate"><b>${esc(p.placa)}</b></span></button>`).join('')
    : '<span class="empty">Nenhum avulso aguardando pagamento agora. Digite sua placa.</span>';
  const pp = $('p-plates'); if (pp.dataset.html !== html) { pp.innerHTML = html; pp.dataset.html = html; }
  const pg = S.pagamento, msg = $('p-msg');
  const form = $('pay-form-area'), done = $('pay-done-area');
  if (pg?.estado === 'ok') {
    form.hidden = true; done.hidden = false;
    if (done.dataset.placa !== pg.placa) {
      done.dataset.placa = pg.placa;
      done.innerHTML = `<div class="pay-done" role="status"><div class="big">${icon('check')}</div><h2>Pagamento confirmado</h2>
        <span class="plate"><b>${esc(pg.placa)}</b></span><p class="sublabel">${reais(VALOR_AVULSO)} recebidos. A cancela abre na saída.</p>
        <button class="btn" id="p-novo">Pagar outra placa</button></div>`;
    }
  } else {
    form.hidden = false; done.hidden = true; done.dataset.placa = '';
    if (pg?.estado === 'enviando') { msg.className = 'pay-msg'; msg.innerHTML = '<span class="spinner"></span>Enviado. Aguardando a confirmação da cancela (CPS2)…'; }
    else if (pg?.estado === 'erro') { msg.className = 'pay-msg erro'; msg.textContent = 'A cancela recusou: essa placa não está dentro como avulso.'; }
    else if (pg?.estado === 'sem_resposta') { msg.className = 'pay-msg erro'; msg.textContent = 'O CPS2 não respondeu. Confira se ele está online e tente de novo.'; }
  }
  $('p-dot').style.background = S.conn === 'conectado' ? 'var(--good)' : 'var(--warning)';
  $('p-conn').textContent = S.conn === 'conectado' ? 'Conectado ao broker MQTT' : 'Conectando ao broker…';
}

// avisos no canto da tela
function toast(html, erro = false) {
  const el = document.createElement('div');
  el.className = 'toast' + (erro ? ' erro' : ''); el.dataset.entrando = '';
  el.innerHTML = icon(erro ? 'alert' : 'check') + `<span>${html}</span>`;
  const box = $('toasts'); box.appendChild(el);
  while (box.children.length > 3) box.firstChild.remove();
  requestAnimationFrame(() => requestAnimationFrame(() => delete el.dataset.entrando));
  setTimeout(() => { el.dataset.entrando = ''; setTimeout(() => el.remove(), 220); }, 2400);
}

// botoes do operador
document.addEventListener('click', (ev) => {
  const b = ev.target.closest('[data-acao]');
  if (!b || b.disabled) return;
  const a = b.dataset.acao;
  if (a === 'manutencao') publicar('cps1/comando', { manutencao: b.dataset.vaga, ativo: b.dataset.ativo === 'true' });
  if (a === 'abrir') publicar('cps2/comando', { cancela: 'abrir' });
  if (a === 'emergencia') publicar('cps2/comando', { modo: S.e2?.modo === 'emergencia' ? 'normal' : 'emergencia' });
  if (a === 'atender') publicar('cps3/comando', { ajuda: 'atendido' });
  if (a === 'brilho') { if (publicar('cps3/comando', { brilho: b.dataset.v })) { S.brilhoModo = b.dataset.v; agendarRender(); } }
});
$('cam-form').addEventListener('submit', (ev) => {
  ev.preventDefault();
  const placa = normPlaca($('cam-placa').value);
  if (placa.length < 7) { toast('A placa precisa de 7 letras e números.', true); return; }
  publicar('cps2/comando', { placa, sentido: $('cam-sentido').value });
});
$('cam-placa').addEventListener('input', (e) => { e.target.value = normPlaca(e.target.value); });
$('p-placa').addEventListener('input', (e) => { e.target.value = normPlaca(e.target.value); $('p-msg').textContent = ''; agendarRender(); });
$('p-plates').addEventListener('click', (e) => { const b = e.target.closest('[data-placa]'); if (b) { $('p-placa').value = b.dataset.placa; $('p-msg').textContent = ''; agendarRender(); } });
$('p-pagar').addEventListener('click', pagar);
$('pay-done-area').addEventListener('click', (e) => { if (e.target.closest('#p-novo')) { S.pagamento = null; $('p-placa').value = ''; $('p-msg').textContent = ''; agendarRender(); } });
$('log-filtro').addEventListener('input', () => { logMudou = true; agendarRender(); });
$('log-sys').addEventListener('change', () => { logMudou = true; agendarRender(); });
$('spark').addEventListener('mousemove', sparkHover);
$('spark').addEventListener('mouseleave', () => { $('spark').classList.remove('hover'); $('spark-x')?.setAttribute('opacity', '0'); });
$('btn-giro').addEventListener('click', (e) => {
  if (!gemeo) return;
  const ligado = gemeo.alternarGiro();
  e.currentTarget.setAttribute('aria-pressed', ligado); e.currentTarget.textContent = ligado ? 'Pausar giro' : 'Girar câmera';
});
window.addEventListener('resize', () => renderSpark());

// troca de aba (?pagina=pagar abre direto a pagina do celular)
function mostrarPagina(nome, empurrar = true) {
  for (const v of ['operador', 'pagar', 'mapa']) {
    $('view-' + v).hidden = v !== nome;
    $('tab-' + v).setAttribute('aria-selected', v === nome);
  }
  if (empurrar) {
    const u = new URL(location.href);
    if (nome === 'operador') u.searchParams.delete('pagina'); else u.searchParams.set('pagina', nome);
    history.replaceState(null, '', u);
  }
  if (nome === 'mapa') abrirMapa();
  agendarRender();
}
document.querySelector('.tabs').addEventListener('click', (e) => { const b = e.target.closest('[data-view]'); if (b) mostrarPagina(b.dataset.view); });
document.querySelector('.tabs').addEventListener('keydown', (e) => {
  if (!['ArrowLeft', 'ArrowRight'].includes(e.key)) return;
  const tabs = [...document.querySelectorAll('.tabs [role=tab]')];
  const i = tabs.indexOf(document.activeElement); if (i < 0) return;
  const n = tabs[(i + (e.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length]; n.focus(); mostrarPagina(n.dataset.view);
});
{ // link da pagina do celular
  const u = new URL(location.href); u.search = ''; u.searchParams.set('pagina', 'pagar');
  if (params.get('broker')) u.searchParams.set('broker', BROKER);
  if (params.get('prefixo')) u.searchParams.set('prefixo', PREFIXO);
  $('p-link').href = u.toString(); $('p-link').textContent = u.toString();
}

// mapa da PUC, so carrega quando abre a aba
let mapaMarcador = null, mapaIniciado = false;
function carregar(tag, attrs) { return new Promise((ok, erro) => { const el = Object.assign(document.createElement(tag), attrs); el.onload = ok; el.onerror = erro; document.head.appendChild(el); }); }
async function abrirMapa() {
  if (mapaIniciado) return; mapaIniciado = true;
  try {
    await Promise.all([
      carregar('link', { rel: 'stylesheet', href: 'https://unpkg.com/maplibre-gl@5.6.0/dist/maplibre-gl.css' }),
      carregar('script', { src: 'https://unpkg.com/maplibre-gl@5.6.0/dist/maplibre-gl.js' }),
    ]);
    const mapa = new maplibregl.Map({
      container: 'mapa', style: 'https://tiles.openfreemap.org/styles/liberty',
      center: [-49.2511, -25.4524], zoom: 17.2, pitch: 62, bearing: -28, attributionControl: { compact: true },
    });
    mapa.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'top-right');
    const el = document.createElement('div'); el.className = 'map-marker';
    mapaMarcador = new maplibregl.Marker({ element: el, anchor: 'bottom' }).setLngLat([-49.2511593, -25.4527391]).addTo(mapa);
    atualizarMapa();
  } catch { $('mapa').innerHTML = '<p class="twin-fallback" style="color:var(--muted)">Não foi possível carregar o mapa.</p>'; }
}
function atualizarMapa() {
  const s1 = S.s1;
  mapaMarcador.getElement().innerHTML = `<b>${s1 ? s1.livres : '–'}</b>vagas livres<br><small>demo: bolsão simulado</small>`;
}

// tem que ficar depois do mapa senao ?pagina=mapa da erro
const paginaInicial = params.get('pagina');
if (paginaInicial === 'pagar') { document.body.classList.add('celular'); mostrarPagina('pagar', false); }
else if (paginaInicial === 'mapa') mostrarPagina('mapa', false);

// gemeo digital 3D com three.js, desenha o estado S
let gemeo = null;
async function iniciarGemeo(host) {
  const THREE = await import('three');
  const { OrbitControls } = await import('three/addons/controls/OrbitControls.js');
  const { CSS2DRenderer, CSS2DObject } = await import('three/addons/renderers/CSS2DRenderer.js');
  const reduz = matchMedia('(prefers-reduced-motion: reduce)').matches;

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  host.appendChild(renderer.domElement);
  const rotulos = new CSS2DRenderer(); rotulos.domElement.className = 'twin-labels'; host.appendChild(rotulos.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0e1526);
  scene.fog = new THREE.Fog(0x0e1526, 38, 75);
  const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 200);
  camera.position.set(5, 10, 21);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(2.4, 2.9, -0.8);
  controls.enableDamping = true; controls.enablePan = false;
  controls.autoRotate = !reduz; controls.autoRotateSpeed = 0.45;
  controls.minDistance = 10; controls.maxDistance = 44; controls.maxPolarAngle = Math.PI * 0.46;
  if (reduz) { $('btn-giro').setAttribute('aria-pressed', 'false'); $('btn-giro').textContent = 'Girar câmera'; }

  scene.add(new THREE.HemisphereLight(0xdbe4ff, 0x1a2236, 1.9));
  const sol = new THREE.DirectionalLight(0xffffff, 2.2);
  sol.position.set(10, 18, 9); sol.castShadow = true; sol.shadow.mapSize.set(2048, 2048);
  Object.assign(sol.shadow.camera, { left: -18, right: 18, top: 18, bottom: -18 }); sol.shadow.bias = -0.0005;
  scene.add(sol);

  const mat = (color, extra = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.8, metalness: 0.05, ...extra });
  const caixa = (w, h, d, m) => { const o = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m); o.castShadow = o.receiveShadow = true; return o; };
  const rotulo = (html, cls = '') => { const el = document.createElement('div'); el.className = 'tlabel ' + cls; el.innerHTML = html; return new CSS2DObject(el); };

  // chao e faixas
  const chao = new THREE.Mesh(new THREE.PlaneGeometry(90, 70), mat(0x172238)); chao.rotation.x = -Math.PI / 2; chao.receiveShadow = true; scene.add(chao);
  const asfalto = new THREE.Mesh(new THREE.PlaneGeometry(27, 15), mat(0x2c374f)); asfalto.rotation.x = -Math.PI / 2; asfalto.position.set(3, 0.01, -1); asfalto.receiveShadow = true; scene.add(asfalto);
  const tinta = mat(0xd9dee7, { roughness: 0.5 });
  const XS = [-4.2, -1.4, 1.4, 4.2], ZV = -4.6;
  for (const x of [-5.6, -2.8, 0, 2.8, 5.6]) { const l = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.02, 5), tinta); l.position.set(x, 0.02, ZV); scene.add(l); }
  { const l = new THREE.Mesh(new THREE.BoxGeometry(11.3, 0.02, 0.1), tinta); l.position.set(0, 0.02, ZV - 2.5); scene.add(l); }
  for (let x = -5; x < 15; x += 2.2) { const l = new THREE.Mesh(new THREE.BoxGeometry(1.1, 0.02, 0.12), mat(0xe5a500, { roughness: 0.5 })); l.position.set(x, 0.02, 0.9); scene.add(l); }

  // carro
  function carro(cor) {
    const g = new THREE.Group();
    const corpo = caixa(1.8, 0.6, 4, mat(cor, { roughness: 0.35, metalness: 0.35 })); corpo.position.y = 0.6; g.add(corpo);
    const cab = caixa(1.55, 0.5, 2.1, mat(0x0f172a, { roughness: 0.15, metalness: 0.6 })); cab.position.set(0, 1.15, -0.2); g.add(cab);
    const rodaGeo = new THREE.CylinderGeometry(0.36, 0.36, 0.26, 18); rodaGeo.rotateZ(Math.PI / 2);
    for (const [x, z] of [[-0.9, 1.3], [0.9, 1.3], [-0.9, -1.3], [0.9, -1.3]]) { const r = new THREE.Mesh(rodaGeo, mat(0x0b0f19)); r.position.set(x, 0.36, z); r.castShadow = true; g.add(r); }
    for (const x of [-0.6, 0.6]) {
      const f = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.14, 0.05), new THREE.MeshBasicMaterial({ color: 0xfff7d6 })); f.position.set(x, 0.72, 2.01); g.add(f);
      const t = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.14, 0.05), new THREE.MeshBasicMaterial({ color: 0xb91c1c })); t.position.set(x, 0.72, -2.01); g.add(t);
    }
    return g;
  }

  // vagas com LED e carro
  const CORES_CARRO = [0xcbd5e1, 0x475569, 0xf8fafc, 0x1e3a8a];
  const vagas3d = XS.map((x, i) => {
    const piso = new THREE.Mesh(new THREE.PlaneGeometry(2.4, 4.6), new THREE.MeshBasicMaterial({ color: COR_VAGA.nd, transparent: true, opacity: 0.22, depthWrite: false }));
    piso.rotation.x = -Math.PI / 2; piso.position.set(x, 0.025, ZV); scene.add(piso);
    const poste = caixa(0.12, 1.3, 0.12, mat(0x334155)); poste.position.set(x, 0.65, ZV - 2.3); scene.add(poste);
    const ledMat = new THREE.MeshStandardMaterial({ color: 0x111827, emissive: new THREE.Color(COR_VAGA.nd), emissiveIntensity: 1.6 });
    const led = new THREE.Mesh(new THREE.SphereGeometry(0.2, 20, 14), ledMat); led.position.set(x, 1.45, ZV - 2.3); scene.add(led);
    const c = carro(CORES_CARRO[i]); c.position.set(x, 4, ZV + 0.1); c.visible = false; scene.add(c);
    const lb = rotulo(`V${i + 1}`, 'vaga'); lb.position.set(x, 0.1, ZV + 2.9); scene.add(lb);
    return { piso, ledMat, carro: c, rot: lb, y: 4 };
  });

  // cancela
  const GX = 8.2, GZ = 3.6;
  const posteC = caixa(0.55, 1.2, 0.55, mat(0x3d434f)); posteC.position.set(GX, 0.6, GZ); scene.add(posteC);
  const pivo = new THREE.Group(); pivo.position.set(GX, 1.0, GZ - 0.3); scene.add(pivo);
  for (let i = 0; i < 6; i++) {
    const s = caixa(0.14, 0.14, 0.78, mat(i % 2 ? 0xf8fafc : 0xdc2626, { roughness: 0.5 })); s.position.set(0, 0, -0.39 - i * 0.78); pivo.add(s);
  }
  const luzC = new THREE.Mesh(new THREE.SphereGeometry(0.13, 16, 12), new THREE.MeshStandardMaterial({ color: 0x111827, emissive: 0xdc2626, emissiveIntensity: 2 }));
  luzC.position.set(GX, 1.85, GZ); scene.add(luzC);
  const carroPortao = carro(0x7c3aed); carroPortao.rotation.y = -Math.PI / 2; carroPortao.position.set(GX + 3.2, 0, 0.9 - 1.2 + 1.0); carroPortao.visible = false; scene.add(carroPortao);
  const lbCancela = rotulo('<i style="--c:#eb6834"></i>CPS2 Cancela'); lbCancela.position.set(GX, 2.6, GZ); scene.add(lbCancela);

  // totem com display, LED e fita
  const TX = 12.2, TZ = 4.4;
  const totem = new THREE.Group(); totem.position.set(TX, 0, TZ); totem.rotation.y = -0.45; scene.add(totem);
  const corpoT = caixa(1.4, 3, 0.45, mat(0x1f2937, { roughness: 0.5 })); corpoT.position.y = 1.5; totem.add(corpoT);
  const cv = document.createElement('canvas'); cv.width = 440; cv.height = 168;
  const texDisplay = new THREE.CanvasTexture(cv); texDisplay.colorSpace = THREE.SRGBColorSpace;
  const tela = new THREE.Mesh(new THREE.PlaneGeometry(1.2, 0.46), new THREE.MeshBasicMaterial({ map: texDisplay, toneMapped: false })); tela.position.set(0, 2.45, 0.231); totem.add(tela);
  const esfera = new THREE.SphereGeometry(0.1, 16, 12);
  const ledT = new THREE.MeshStandardMaterial({ color: 0x111827, emissive: 0x22c55e, emissiveIntensity: 0 });
  const ledTm = new THREE.Mesh(esfera, ledT); ledTm.position.set(-0.4, 2.0, 0.24); totem.add(ledTm);
  const azulT = new THREE.MeshStandardMaterial({ color: 0x111827, emissive: 0x3b82f6, emissiveIntensity: 0 });
  const azulTm = new THREE.Mesh(esfera, azulT); azulTm.position.set(0.4, 2.0, 0.24); totem.add(azulTm);
  const pixels = [0, 1, 2, 3].map((i) => {
    const m = new THREE.MeshStandardMaterial({ color: 0x111827, emissive: 0x000000, emissiveIntensity: 2 });
    const p = new THREE.Mesh(new THREE.SphereGeometry(0.11, 16, 12), m); p.position.set(-0.42 + i * 0.28, 1.62, 0.24); totem.add(p); return m;
  });
  const lbTotem = rotulo('<i style="--c:#1baf7a"></i>CPS3 Totem'); lbTotem.position.set(0, 3.5, 0); totem.add(lbTotem);

  // placas ESP32 e o broker
  function placaEsp(x, y, z) {
    const g = new THREE.Group(); g.position.set(x, y, z);
    const pcb = caixa(0.8, 0.08, 0.5, mat(0x14532d, { roughness: 0.6 })); g.add(pcb);
    const chip = caixa(0.34, 0.08, 0.28, mat(0xc0c7d1, { metalness: 0.7, roughness: 0.3 })); chip.position.y = 0.08; g.add(chip);
    scene.add(g); return g;
  }
  const posteCps1 = caixa(0.14, 2.5, 0.14, mat(0x334155)); posteCps1.position.set(-6.7, 1.25, ZV); scene.add(posteCps1);
  const esp1 = placaEsp(-6.7, 2.55, ZV);
  const lbCps1 = rotulo('<i style="--c:#2a78d6"></i>CPS1 Vagas'); lbCps1.position.set(-6.7, 3.3, ZV); scene.add(lbCps1);
  const esp2 = placaEsp(GX, 1.25, GZ);
  const esp3 = placaEsp(0, 3.05, 0); totem.add(esp3);   // prende a placa no totem

  // monitor do dashboard
  const DX = -8.6, DZ = 3.4;
  const pe = caixa(0.15, 1.6, 0.15, mat(0x334155)); pe.position.set(DX, 0.8, DZ); scene.add(pe);
  const monitor = caixa(2.4, 1.4, 0.12, mat(0x0f172a)); monitor.position.set(DX, 2.2, DZ); monitor.rotation.y = 0.5; scene.add(monitor);
  const telaD = new THREE.Mesh(new THREE.PlaneGeometry(2.2, 1.2), new THREE.MeshBasicMaterial({ color: 0x1e3a5f })); telaD.position.set(0, 0, 0.065); monitor.add(telaD);
  const lbDash = rotulo('<i style="--c:#9aa1ad"></i>Dashboard'); lbDash.position.set(DX, 3.3, DZ); scene.add(lbDash);

  const BROKER_POS = new THREE.Vector3(2, 6.6, -2);
  const broker = new THREE.Mesh(new THREE.IcosahedronGeometry(0.7, 1), new THREE.MeshStandardMaterial({ color: 0x1e293b, emissive: 0x818cf8, emissiveIntensity: 0.7, flatShading: true }));
  broker.position.copy(BROKER_POS); scene.add(broker);
  const anel = new THREE.Mesh(new THREE.TorusGeometry(1.15, 0.025, 8, 64), new THREE.MeshBasicMaterial({ color: 0x818cf8, transparent: true, opacity: 0.6 }));
  anel.position.copy(BROKER_POS); anel.rotation.x = Math.PI / 2.3; scene.add(anel);
  const lbBroker = rotulo('<i style="--c:#818cf8"></i>Broker MQTT'); lbBroker.position.copy(BROKER_POS).add(new THREE.Vector3(0, 1.3, 0)); scene.add(lbBroker);

  // de onde saem e chegam os pulsos
  const ponto = (o) => { const v = new THREE.Vector3(); o.getWorldPosition(v); return v; };
  scene.updateMatrixWorld(true);
  const NOS = { cps1: ponto(esp1), cps2: ponto(esp2), cps3: ponto(esp3), dash: ponto(monitor) };
  const OBJ = { cps1: esp1, cps2: esp2, cps3: esp3, dash: monitor };
  const COR_SIS = { cps1: 0x3987e5, cps2: 0xd95926, cps3: 0x199e70, dash: 0xe2e8f0 };
  const curva = (a, b) => { const m = a.clone().lerp(b, 0.5); m.y += 1.8; return new THREE.QuadraticBezierCurve3(a.clone(), m, b.clone()); };
  for (const k in NOS) {
    const pts = curva(NOS[k], BROKER_POS).getPoints(40);
    scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineDashedMaterial({ color: 0x4b5a78, dashSize: 0.25, gapSize: 0.18, transparent: true, opacity: 0.7 })).computeLineDistances());
  }

  // textura dos pulsos
  const gc = document.createElement('canvas'); gc.width = gc.height = 64;
  const gx = gc.getContext('2d'); const grad = gx.createRadialGradient(32, 32, 0, 32, 32, 32);
  grad.addColorStop(0, 'rgba(255,255,255,1)'); grad.addColorStop(0.25, 'rgba(255,255,255,.8)'); grad.addColorStop(1, 'rgba(255,255,255,0)');
  gx.fillStyle = grad; gx.fillRect(0, 0, 64, 64);
  const texBrilho = new THREE.CanvasTexture(gc);

  const pulsos = [];
  const flashes = new Map();   // quanto tempo cada objeto ainda pisca
  function lancar(de, para, cor, dur, aoChegar) {
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: texBrilho, color: cor, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true }));
    sp.scale.setScalar(0.95); scene.add(sp);
    pulsos.push({ sp, c: curva(de, para), t: 0, dur, aoChegar });
  }
  function pulso(rel) {
    const rota = ROTAS[rel];
    if (!rota || pulsos.length > 48) return;
    const [origem, destinos] = rota, cor = COR_SIS[origem];
    flashes.set(OBJ[origem], 0.3);
    lancar(NOS[origem], BROKER_POS, cor, reduz ? 0.3 : 0.9, () => {
      flashes.set(broker, 0.35);
      for (const d of destinos) lancar(BROKER_POS, NOS[d], cor, reduz ? 0.3 : 0.9, () => flashes.set(OBJ[d], 0.3));
    });
  }

  // passa o estado do MQTT pra animacao
  let st = S, ultimoTxt = '';
  function atualizar(novo) { st = novo; }

  const relogio = new THREE.Clock();
  const cor = new THREE.Color();
  function quadro() {
    requestAnimationFrame(quadro);
    if (document.hidden || host.offsetParent === null) return;   // aba escondida nao desenha
    const dt = Math.min(relogio.getDelta(), 0.05), agora = performance.now();
    const pisca = Math.floor(agora / 500) % 2 === 0;

    // vagas
    const vs = st.s1?.vagas || [], leds = st.e1?.leds || [];
    vagas3d.forEach((v, i) => {
      const d = vs[i];
      const chave = !d ? 'nd' : d.interditada ? 'interditada' : d.ocupada ? 'ocupada' : d.tipo;
      v.piso.material.color.set(COR_VAGA[chave] || COR_VAGA.nd);
      const piscando = leds[i] === 'piscando';
      v.piso.material.opacity = piscando ? (pisca ? 0.45 : 0.1) : 0.3;
      v.ledMat.emissive.set(piscando ? (pisca ? COR_VAGA.ocupada : '#000000') : (COR_VAGA[chave] || COR_VAGA.nd));
      if (d) v.rot.element.textContent = `${d.id} ${NOME_TIPO[d.tipo] || ''}`;
      const alvoY = d?.ocupada ? 0 : 4;
      if (d?.ocupada) v.carro.visible = true;
      v.y += (alvoY - v.y) * (reduz ? 1 : Math.min(1, dt * 6));
      v.carro.position.y = v.y;
      if (!d?.ocupada && v.y > 3.9) v.carro.visible = false;
    });

    // cancela
    const e2 = st.e2;
    const alvo = e2?.cancela === 'aberta' ? 1.42 : 0;
    pivo.rotation.x += (alvo - pivo.rotation.x) * (reduz ? 1 : Math.min(1, dt * 3.5));
    const travada = st.alarmes.cancela_travada;
    luzC.material.emissive.set(travada ? (pisca ? 0xef4444 : 0x000000) : e2?.cancela === 'aberta' ? 0x22c55e : 0xdc2626);
    carroPortao.visible = !!e2?.carro;

    // totem
    const e3 = st.e3;
    const txt = textoDisplay(e3 ? e3.display : null) + (e3?.brilho === 'baixo' ? 'b' : 'a');
    if (txt !== ultimoTxt) { desenharDisplay(cv.getContext('2d'), txt.slice(0, 4), cv.width, cv.height, txt[4] === 'a'); texDisplay.needsUpdate = true; ultimoTxt = txt; }
    const led = e3?.led;
    ledT.emissive.set(led === 'verde' ? 0x22c55e : 0xef4444);
    ledT.emissiveIntensity = !led ? 0 : led === 'vermelho_piscando' ? (pisca ? 2 : 0) : 2;
    azulT.emissiveIntensity = e3?.ajuda === 'atendida' ? 2.2 : (e3?.ajuda === 'aguardando' || st.ajudaPedida) ? (pisca ? 2.2 : 0) : 0;
    const fita = e3?.fita || [];
    pixels.forEach((m, i) => { m.emissive.set(COR_LED[fita[i]] || '#000000'); m.emissiveIntensity = (e3?.fita_pisca || e3?.pisca_vaga === i) && !pisca ? 0 : 2; });

    // sistema offline fica vermelho
    for (const [k, o, lb] of [['cps1', esp1, lbCps1], ['cps2', esp2, lbCancela], ['cps3', esp3, lbTotem]]) {
      const off = st.status[k] === 'offline';
      o.children[0].material.color.set(off ? 0x7f1d1d : 0x14532d);
      lb.element.classList.toggle('off', off);
    }

    // pulsos das mensagens
    for (let i = pulsos.length - 1; i >= 0; i--) {
      const p = pulsos[i]; p.t += dt / p.dur;
      const k = Math.min(p.t, 1), e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
      p.sp.position.copy(p.c.getPoint(e));
      if (p.t >= 1) { scene.remove(p.sp); p.sp.material.dispose(); pulsos.splice(i, 1); p.aoChegar?.(); }
    }
    for (const [o, tempo] of flashes) {
      const r = tempo - dt; const s = 1 + Math.max(0, r) * 0.9;
      o.scale.setScalar(s);
      if (r <= 0) { o.scale.setScalar(1); flashes.delete(o); } else flashes.set(o, r);
    }
    broker.rotation.y += dt * 0.4; anel.rotation.z += dt * 0.6;
    controls.update();
    renderer.render(scene, camera);
    rotulos.render(scene, camera);
  }

  function ajustar() {
    const w = host.clientWidth, h = host.clientHeight; if (!w || !h) return;
    renderer.setSize(w, h); rotulos.setSize(w, h); camera.aspect = w / h; camera.updateProjectionMatrix();
  }
  new ResizeObserver(ajustar).observe(host); ajustar();
  quadro();
  return {
    atualizar, pulso, alternarGiro: () => (controls.autoRotate = !controls.autoRotate),
    resumo: () => ({ carros: vagas3d.map((v) => v.carro.visible), bracoCancela: +pivo.rotation.x.toFixed(2), pulsos: pulsos.length }),
  };
}

// inicio
// pra testar no console: smartpark.estado
window.smartpark = { estado: S, gemeo: () => gemeo };
conectar();
agendarRender();
iniciarGemeo($('twin')).then((g) => { gemeo = g; g.atualizar(S); })
  .catch((e) => { console.warn('3D indisponível:', e); $('twin').innerHTML = '<div class="twin-fallback">O 3D não carregou. O resto do painel funciona normalmente.<br><small></small></div>'; $('twin').querySelector('small').textContent = String(e && e.message || e); });
