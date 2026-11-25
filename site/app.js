const $ = (selector) => document.querySelector(selector);
let collection = [];
let currentUser = null;
const text = (value, fallback = '—') => value === null || value === undefined || value === '' ? fallback : String(value);
const number = (value) => new Intl.NumberFormat('pt-BR').format(Number(value || 0));
// Manter sincronizado com VERSAO_ARTES em sistemas/cartas.py.
const CARD_IMAGE_VERSION = 28;
const imageUrl = (card) => {
  const raw = card.image_url || `/api/gwent/cards/${encodeURIComponent(card.card_id || String(card.id || '').split('::')[0])}/image`;
  if (!raw.includes('/api/gwent/cards/')) return raw;
  const url = new URL(raw, window.location.origin);
  if (!url.searchParams.has('v')) url.searchParams.set('v', String(CARD_IMAGE_VERSION));
  // Grade/deck usam miniatura. O modal pede perfil HD independente.
  if (!url.searchParams.has('detail')) url.searchParams.set('thumb', '1');
  return `${url.pathname}${url.search}`;
};
const cardImageMarkup = (card, alt = '') =>
  `<img data-card-src="${escapeHTML(imageUrl(card))}" loading="lazy" decoding="async" alt="${escapeHTML(alt)}">`;
// V51 — linguagem visual semântica das cartas (ícones vetoriais locais, sem dependência externa).
const CARD_SIGILS = {
  'ordem áurea': '✦', 'véu carmesim': '血', 'lua negra': '☾',
  'corpo a corpo': '⚔', 'longa distância': '➶', 'cerco': '⌖',
  'especial': '◇', 'relíquia': '♜', 'primordial': '✹'
};
const normalizeCardLabel = value => String(value || '').normalize('NFD')
  .replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('pt-BR');
const cardSigil = value => {
  const key = normalizeCardLabel(value);
  return CARD_SIGILS[key] || (key.includes('lua') ? '☾' : key.includes('sangue') ? '血'
    : key.includes('fogo') || key.includes('chama') ? '♨'
    : key.includes('gelo') || key.includes('geada') ? '❄'
    : key.includes('morte') || key.includes('exec') ? '†'
    : key.includes('invoc') || key.includes('espir') ? '♧'
    : key.includes('escud') || key.includes('protec') ? '⬡'
    : key.includes('venen') || key.includes('podrid') ? '☣'
    : key.includes('louc') || key.includes('frenes') ? '◉'
    : key.includes('cura') || key.includes('purif') ? '✧'
    : key.includes('Especial') ? '◇' : '✦');
};
const RARITY_POWER = {'Comum':0,'Rara':1,'Épica':2,'Lendária':3,'Mítica':4,'Primordial':5,'Singular':6};
const rarityPower = card => Number.isFinite(Number(card?.potencia_raridade)) ? Number(card.potencia_raridade) : (RARITY_POWER[card?.raridade] ?? 0);
const rarityPowerMarkup = card => `<span class=\"v54-rarity-power\" title=\"Potência da raridade: amplia habilidades; não é poder de ataque\"><i>✦</i> Potência ${rarityPower(card)}</span>`;
const cardInsigniaMarkup = card => {
  const category = card.categoria === 'Especial' ? 'Especial' : 'Unidade';
  const faction = card.faccao || card.tipo || 'Sem facção';
  const row = card.row_label || card.fileira || (category === 'Especial' ? 'Efeito' : 'Fileira não informada');
  const rarity = card.raridade || 'Comum';
  const ability = card.habilidade_nome || card.efeito_nome || card.habilidade || card.efeito || '';
  if (category === 'Especial') {
    const effect = card.habilidade_texto || card.texto_efeito || 'Efeito especial';
    return `<div class="v51-special-banner"><span><i>◇</i> CARTA ESPECIAL</span><span>${escapeHTML(rarity)}</span></div><div class="v54-card-rarity-line">${rarityPowerMarkup(card)}<small>Escala do efeito · não soma ao poder-base</small></div><div class="v51-card-bottomline v51-special-effect"><span title="${escapeHTML(effect)}"><i>${cardSigil(effect)}</i>${escapeHTML(effect)}</span></div>`;
  }
  return `<div class="v51-card-topline"><span class="v51-card-faction" title="${escapeHTML(faction)}"><i>${cardSigil(faction)}</i>${escapeHTML(faction)}</span><span class="v51-card-rarity">${escapeHTML(rarity)}</span></div><div class="v54-card-rarity-line">${rarityPowerMarkup(card)}<small>Escala do efeito · não soma ao poder-base</small></div><div class="v51-card-bottomline"><span title="${escapeHTML(row)}"><i>${cardSigil(row)}</i>${escapeHTML(row)}</span>${ability ? `<span class="v51-card-ability" title="${escapeHTML(ability)}"><i>${cardSigil(ability)}</i>${escapeHTML(ability)}</span>` : `<span class="v51-card-ability v51-no-ability"><i>—</i>Força pura</span>`}</div>`;
};
const CARD_IMAGE_FALLBACK = `data:image/svg+xml,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 620"><rect width="420" height="620" rx="20" fill="#17131c"/><rect x="18" y="18" width="384" height="584" rx="16" fill="none" stroke="#9b805a" stroke-width="4"/><path d="M210 190l55 55-55 55-55-55z" fill="none" stroke="#9b805a" stroke-width="8"/><text x="210" y="390" fill="#d8c6a6" font-family="sans-serif" font-size="22" text-anchor="middle">ARTE INDISPONÍVEL</text><text x="210" y="425" fill="#978a9b" font-family="sans-serif" font-size="16" text-anchor="middle">Tente recarregar a página</text></svg>')}`;
const CARD_IMAGE_RETRY_DELAYS = [700, 1600];
const CARD_IMAGE_MAX_ACTIVE = 4;
const cardImageQueue = [];
let cardImageActive = 0;
function enqueueCardImage(image, source = image?.dataset.cardSrc) {
  if (!(image instanceof HTMLImageElement) || !source || image.dataset.cardImageFallback === 'true') return;
  if (image.dataset.cardImageQueued === 'true' || image.dataset.cardImageActive === 'true') return;
  image.dataset.cardPendingSrc = source;
  image.dataset.cardImageQueued = 'true';
  cardImageQueue.push(image);
  pumpCardImages();
}
function pumpCardImages() {
  while (cardImageActive < CARD_IMAGE_MAX_ACTIVE && cardImageQueue.length) {
    const image = cardImageQueue.shift();
    if (!(image instanceof HTMLImageElement) || !image.isConnected) continue;
    image.dataset.cardImageQueued = 'false';
    image.dataset.cardImageActive = 'true';
    cardImageActive += 1;
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      image.dataset.cardImageActive = 'false';
      cardImageActive = Math.max(0, cardImageActive - 1);
      pumpCardImages();
    };
    image.addEventListener('load', finish, {once:true});
    image.addEventListener('error', finish, {once:true});
    image.src = image.dataset.cardPendingSrc || image.dataset.cardSrc;
  }
}
let cardImageObserver = null;
if ('IntersectionObserver' in window) {
  cardImageObserver = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      cardImageObserver.unobserve(entry.target);
      enqueueCardImage(entry.target);
    }
  }, {rootMargin:'360px 0px', threshold:0.01});
}
function observeCardImages(root) {
  if (!root) return;
  const images = [];
  if (root instanceof HTMLImageElement && root.hasAttribute('data-card-src')) images.push(root);
  if (root.querySelectorAll) images.push(...root.querySelectorAll('img[data-card-src]'));
  for (const image of images) {
    if (image.dataset.cardImageObserved === 'true') continue;
    image.dataset.cardImageObserved = 'true';
    if (cardImageObserver) cardImageObserver.observe(image);
    else enqueueCardImage(image);
  }
}
// Observa conteúdo dinâmico: a galeria só inicia as quatro imagens mais próximas da tela.
if (document.body && 'MutationObserver' in window) {
  const cardMutationObserver = new MutationObserver(records => {
    for (const record of records) for (const node of record.addedNodes) {
      if (node.nodeType === Node.ELEMENT_NODE) observeCardImages(node);
    }
  });
  cardMutationObserver.observe(document.body, {childList:true, subtree:true});
}
document.addEventListener('error', (event) => {
  const image = event.target;
  if (!(image instanceof HTMLImageElement) || !image.src.includes('/api/gwent/cards/')) return;
  const attempts = Number(image.dataset.cardRetry || 0);
  if (attempts < CARD_IMAGE_RETRY_DELAYS.length) {
    image.dataset.cardRetry = String(attempts + 1);
    const original = image.dataset.cardOriginalSrc || image.dataset.cardSrc || image.src;
    image.dataset.cardOriginalSrc = original;
    window.setTimeout(() => {
      const retryUrl = new URL(original, window.location.origin);
      retryUrl.searchParams.set('_retry', String(attempts + 1));
      enqueueCardImage(image, `${retryUrl.pathname}${retryUrl.search}`);
    }, CARD_IMAGE_RETRY_DELAYS[attempts]);
    return;
  }
  image.dataset.cardImageFallback = 'true';
  image.src = CARD_IMAGE_FALLBACK;
  image.alt = 'Imagem da carta indisponível';
}, true);
function escapeHTML(value) { return String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch])); }
function showNotice(message, kind = 'info') {
  const el = $('#notice'); if (el) { el.textContent = message; el.className = `notice ${kind}`; el.hidden = !message; }
  if (!message) return;
  let t = document.getElementById('toast');
  if (!t) { t = document.createElement('div'); t.id = 'toast'; t.setAttribute('role', 'status'); document.body.appendChild(t); }
  t.textContent = message; t.className = `toast ${kind} show`;
  clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove('show'), 5000);
}
async function loadAccount() {
  try {
    const meResponse = await fetch('/api/me', {credentials:'same-origin', cache:'no-store'});
    if (!meResponse.ok) {
      currentUser = null;
      $('#profile-name').textContent = 'Visitante';
      $('#profile-status').textContent = 'Conecte sua conta Discord';
      $('#login-button').hidden = false; $('#logout-button').hidden = true;
      collection = [];
      showNotice('Entre com sua conta Discord para acessar o Gwent.');
      return;
    }
    const me = await meResponse.json(); currentUser = me.user;
    $('#profile-name').textContent = $('#profile-name').dataset.n || 'Conta Discord';
    $('#profile-status').textContent = $('#profile-status').dataset.s || `ID ${text(currentUser?.id)}`;
    $('#login-button').hidden = true; $('#logout-button').hidden = false;
    const response = await fetch('/api/gwent/cards', {credentials:'same-origin', cache:'no-store'});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Falha ao carregar cartas do Gwent.');
    collection = Array.isArray(data.cards) ? data.cards : [];
    $('#souls').textContent = number(data.summary?.souls);
    $('#fragments').textContent = number(data.summary?.fragments);
    $('#denarios').textContent = number(data.summary?.denarios);
    $('#gwent-xp').textContent = number(data.summary?.xp);
    showNotice(`Gwent sincronizado: ${collection.length} cartas disponíveis.`, 'success');
  } catch (error) { showNotice(error.message || 'Falha ao conectar ao servidor.', 'error'); }
}
$('#login-button').addEventListener('click', () => { const next = window.location.pathname + window.location.search; window.location.href = `/auth/discord/login?next=${encodeURIComponent(next)}`; });
$('#logout-button').addEventListener('click', async () => { await fetch('/auth/logout', {method:'POST', credentials:'same-origin'}); window.location.href = '/'; });

// --- Motor e interface do Gwent do Coliseu. ---
let gwentDeckIds = [];
let gwentSavedIds = [];
let gwentSavedFaction = 'Ordem Áurea';
let gwentSavedLeader = 'comandante_fornalha';
let gwentSavedRelic = '';
let gwentLeaderOptions = [];
let currentGwentMatch = null;
let currentGwentData = null;
let gwentMatchFinished = false;
let gwentPoll = null;
let gwentListPoll = null;
// Evita reconstruir a arena (e baixar novamente as imagens) quando o estado não mudou.
let gwentLastRenderSignature = '';
let gwentRefreshPromise = null;
let gwentRefreshEpoch = 0;
let gwentActionInFlight = false;
let gwentInitialSnapshotLoaded = false;
let gwentSeenRoundCount = 0;
let gwentPreviouslyFinished = false;
// null = automático. O padrão abre na preparação/vez do jogador e recolhe na vez adversária.
let gwentHandOpen = null;
let gwentHandLastPhase = null;
let gwentSelectedHandCard = '';
let gwentHandCardsById = new Map();
let gwentLastTurnAnnouncement = null;
let gwentLastViewportWidth = window.innerWidth;

const gwentRows = [
  ['melee', 'Corpo a corpo'], ['ranged', 'Longa distância'], ['siege', 'Cerco']
];

function updateGwentSelectedCardUI(cardId = gwentSelectedHandCard) {
  const arena = $('#gwent-arena');
  if (!arena) return;
  const id = String(cardId || '');
  const card = gwentHandCardsById.get(id) || null;
  gwentSelectedHandCard = card ? id : '';

  arena.querySelectorAll('[data-gwent-hand-card]').forEach(article => {
    const selected = article.dataset.gwentHandCard === gwentSelectedHandCard;
    article.classList.toggle('is-selected', selected);
    article.setAttribute('aria-pressed', String(selected));
  });

  const name = arena.querySelector('#gwent-selected-name');
  const effect = arena.querySelector('#gwent-selected-effect');
  const detail = arena.querySelector('[data-gwent-selected-details]');
  const row = arena.querySelector('#gwent-selected-row');
  const play = arena.querySelector('[data-gwent-play-selected]');
  const preview = arena.querySelector('#gwent-selected-card-image');

  if (name) name.textContent = card ? (card.nome || 'Carta selecionada') : 'Selecione uma carta';
  if (effect) effect.textContent = card
    ? `${card.habilidade_nome || 'Habilidade'} · ${card.habilidade_texto || 'Sem efeito adicional'}${card.especial ? ' · Carta especial' : ` · ${number(card.poder)} poder`}`
    : 'Clique em uma carta para configurar a jogada.';
  if (detail) detail.hidden = !card;
  if (preview) {
    const handImage = card
      ? arena.querySelector(`[data-gwent-hand-card="${CSS.escape(id)}"] img[data-card-src]`)
      : null;
    preview.replaceChildren(handImage ? handImage.cloneNode(true) : document.createTextNode(''));
    preview.hidden = !card;
  }
  if (row) {
    row.disabled = !card || row.dataset.turnAllowed !== 'true';
    if (card && card.row && [...row.options].some(option => option.value === card.row)) row.value = card.row;
  }
  if (play) play.disabled = !card || play.dataset.turnAllowed !== 'true';
}

const gwentFactionInfo = {
  'Ordem Áurea': { description: 'Luz, lei e fé: defesa, juramentos, proteção e purificação.', leaders: [
    ['comandante_fornalha', 'Godfrey', 'Fortalece +2 todas as unidades aliadas de Corpo a Corpo.'],
    ['bastiao_ancestral', 'Morgott', 'Concede Escudo e +1 a até 2 aliados da fileira escolhida.'],
    ['juiz_cerco', 'Radagon', 'Purifica estados negativos; cada aliado purificado recebe +1.']
  ]},
  'Lua Negra': { description: 'Magia, cosmos e segredos: feitiçaria, gravidade e domínio astral.', leaders: [
    ['arquimaga_eclipse', 'Rennala', 'Remove Geada e Podridão dos aliados; aliados purificados em Cerco recebem +1.'],
    ['mestre_eclipse', 'Astel', 'Aplica Geada aos 3 inimigos mais fortes da fileira escolhida.'],
    ['oraculo_tempestade', 'Loretta', 'Concede +2 às 2 unidades aliadas mais fortes de Longa Distância.']
  ]},
  'Véu Carmesim': { description: 'Sangue, sacrifício e heresia: hemorragia, devoção e corrupção.', leaders: [
    ['mestre_veu', 'Mohg', 'Aplica marcas de Sangramento aos 2 inimigos mais fortes da fileira.'],
    ['sombra_caminhante', 'Rykard', 'Sacrifica o aliado mais fraco e fortalece os demais da fileira.'],
    ['voz_caidos', 'Esgar', 'Ressuscita uma unidade de poder-base até 5 do descarte.']
  ]}
};
// Os líderes vêm do servidor (fonte única); a lista fixa acima serve só de reserva se a API não enviar.
function applyGwentLeaders(byFaction) {
  if (!byFaction) return;
  Object.entries(byFaction).forEach(([faction, list]) => {
    if (!Array.isArray(list) || !list.length || !gwentFactionInfo[faction]) return;
    gwentFactionInfo[faction].leaders = list.map(l => [l.id, l.name, l.description, l.art_url || '', l.default_art_url || '']);
  });
}
function renderGwentLeaderOptions(selected = '') {
  const faction = $('#gwent-faction')?.value || 'Ordem Áurea';
  const info = gwentFactionInfo[faction] || gwentFactionInfo['Ordem Áurea'];
  const select = $('#gwent-leader');
  if (!select) return;
  select.innerHTML = info.leaders.map(([id, name]) => `<option value="${id}">${escapeHTML(name)}</option>`).join('');
  select.value = info.leaders.some(([id]) => id === selected) ? selected : info.leaders[0][0];
  $('#gwent-faction-description').textContent = info.description;
  const leader = info.leaders.find(([id]) => id === select.value) || info.leaders[0];
  const leaderHelp = $('#gwent-leader-description');
  if (leaderHelp) leaderHelp.textContent = `${leader[1]}: ${leader[2]}`;
  const preview = $('#gwent-leader-card');
  if (preview) {
    const sigils = {'Ordem Áurea':'✧','Véu Carmesim':'♜','Lua Negra':'☾'};
    const portraits = {Godfrey:'godfrey',Morgott:'morgott',Radagon:'radagon',Mohg:'mohg',Rykard:'rykard',Esgar:'esgar',Rennala:'rennala',Astel:'astel',Loretta:'loretta'};
    const portrait = portraits[leader[1]] || 'godfrey';
    const hasCustomArt = !!leader[3];
    const artUrl = leader[3] || leader[4] || `assets/leaders/${portrait}.webp`;
    preview.innerHTML = `<div class="gwent-leader-relic v52-leader-card faction-${faction === 'Ordem Áurea' ? 'gold' : faction === 'Véu Carmesim' ? 'blood' : 'moon'} ${hasCustomArt ? 'has-custom-leader-art' : ''}" style="--leader-art:url('${escapeHTML(artUrl)}')"><div class="leader-art-backdrop" aria-hidden="true"></div><div class="leader-relic-sigil">${sigils[faction] || '✦'}</div><small>${escapeHTML(faction)}</small><strong>${escapeHTML(leader[1])}</strong><p>${escapeHTML(leader[2])}</p><em>LÍDER · CARTA DE COMANDO</em></div>`;
  }
}
function renderGwentBuilder() {
  const selected = gwentDeckIds.map(id => collection.find(c => c.id === id)).filter(Boolean);
  const evolutionCost = {Comum:20, Rara:40, 'Épica':80, 'Lendária':160};
  const upgradeCost = {Comum:10, Rara:20, 'Épica':40, 'Lendária':80, 'Mítica':150, 'Primordial':250};
  const specialCount = selected.filter(card => card.categoria === 'Especial').length;
  const unitCount = selected.length - specialCount;
  $('#gwent-deck-count').textContent = `${selected.length}/12 cartas · ${unitCount} unidades · ${specialCount} especiais`;
  const cardTile = (card, inDeck = false) => inDeck
    ? `<button type="button" class="gwent-card-tile gwent-deck-mini is-selected" data-gwent-inspect="${escapeHTML(card.id)}" aria-label="Inspecionar ${escapeHTML(card.nome)}" title="Clique para ver detalhes"><span class="gwent-card-tile-art">${cardImageMarkup(card, card.nome || 'Carta')}</span><span class="gwent-deck-mini-name">${escapeHTML(card.nome || 'Carta')}</span></button>`
    : `<button type="button" class="gwent-card-tile" data-gwent-inspect="${escapeHTML(card.id)}" aria-label="Inspecionar ${escapeHTML(card.nome)}" title="Clique para ver detalhes"><span class="gwent-card-tile-art">${cardImageMarkup(card, card.nome || 'Carta')}</span><span class="gwent-card-tile-hint">VER CARTA</span></button>`;
  $('#gwent-deck-selected').innerHTML = selected.map(card => cardTile(card, true)).join('') || '<div class="empty-state">Selecione 12 cartas da coleção.</div>';
  const q = ($('#gwent-card-search').value || '').trim().toLocaleLowerCase('pt-BR');
  const selectedSet = new Set(selected.map(card => card.card_id || card.id));
  const factionFilter = $('#gwent-filter-faction')?.value || '';
  const rarityFilter = $('#gwent-filter-rarity')?.value || '';
  const pool = collection.filter(c => !selectedSet.has(c.card_id || c.id)
    && (!factionFilter || c.faccao === factionFilter)
    && (!rarityFilter || c.raridade === rarityFilter)
    && (`${c.nome} ${c.faccao} ${c.row_label || c.fileira} ${c.papel_gwent} ${c.categoria} ${c.habilidade} ${c.habilidade_texto} ${c.descricao}`.toLocaleLowerCase('pt-BR').includes(q)));
  $('#gwent-card-pool').innerHTML = pool.map(card => cardTile(card)).join('') || '<div class="empty-state">Nenhuma carta disponível.</div>';
  const selectedFaction = $('#gwent-faction')?.value || 'Ordem Áurea';
  const factionByType = {'Força':'Ordem Áurea','Destreza':'Véu Carmesim','Magia':'Lua Negra'};
  const factionAliases = {'Lua Sombria':'Lua Negra','Casa Cariana':'Lua Negra','Dinastia Mohgwyn':'Véu Carmesim'};
  const factionCounts = {'Ordem Áurea':0,'Véu Carmesim':0,'Lua Negra':0};
  selected.filter(card => card.categoria !== 'Especial').forEach(card => {
    const rawFaction = card.faccao || '';
    const faction = factionAliases[rawFaction] || (Object.prototype.hasOwnProperty.call(factionCounts, rawFaction) ? rawFaction : factionByType[card.tipo] || '');
    if (Object.prototype.hasOwnProperty.call(factionCounts, faction)) factionCounts[faction] += 1;
  });
  const maxFactionCount = Math.max(...Object.values(factionCounts));
  const factionMatches = maxFactionCount > 0 && factionCounts[selectedFaction] === maxFactionCount;
  const configChanged = selectedFaction !== gwentSavedFaction
    || ($('#gwent-leader')?.value || 'comandante_fornalha') !== gwentSavedLeader
    || ($('#gwent-relic-select')?.value || '') !== gwentSavedRelic;
  $('#gwent-save-deck').disabled = selected.length !== 12 || unitCount < 8 || specialCount > 4 || !factionMatches
    || (JSON.stringify(gwentDeckIds) === JSON.stringify(gwentSavedIds) && !configChanged);
  const resetButton = $('#gwent-reset-deck');
  if (resetButton) resetButton.disabled = selected.length === 0 && gwentSavedIds.length === 0;
  $('#gwent-deck-status').textContent = selected.length === 12 && unitCount < 8
    ? 'Inclua pelo menos 8 unidades no deck.'
    : specialCount > 4 ? 'O limite é de 4 cartas especiais por deck.'
    : selected.length === 12 && !factionMatches
      ? `A facção escolhida precisa ser predominante: Ordem Áurea ${factionCounts['Ordem Áurea']} · Véu Carmesim ${factionCounts['Véu Carmesim']} · Lua Negra ${factionCounts['Lua Negra']}.`
      : `${unitCount}/12 unidades e ${specialCount}/4 especiais. Facção predominante: ${selectedFaction}.`;
}


function closeGwentCollectionCardModal() {
  document.getElementById('gwent-collection-card-modal')?.remove();
}
function openGwentCollectionCardModal(cardId) {
  const card = collection.find(item => String(item.id) === String(cardId));
  if (!card) return;
  closeGwentCollectionCardModal();
  const inDeck = gwentDeckIds.includes(card.id);
  const special = card.categoria === 'Especial';
  const abilityName = card.habilidade_nome || card.efeito_nome || (special ? 'Efeito especial' : 'Sem habilidade especial');
  const abilityText = card.habilidade_texto || card.texto_efeito || (special ? 'Efeito não informado.' : 'Esta unidade não possui habilidade especial.');
  const rarityBudget = rarityPower(card);
  const evolveCost = ({Comum:20,Rara:40,'Épica':80,'Lendária':160})[card.raridade];
  const upgradeCost = ({Comum:10,Rara:20,'Épica':40,'Lendária':80,'Mítica':150,'Primordial':250})[card.raridade];
  const canEvolve = !!card.exemplar_id && !special && !!evolveCost;
  const canUpgrade = !!card.exemplar_id && !special && !!upgradeCost && Number(card.poder) < Number(card.max_power);
  const src = imageUrl(card);
  const modalCard = {...card};
  if (src.includes('/api/gwent/cards/')) {
    const hi = new URL(src, window.location.origin);
    hi.searchParams.delete('thumb');
    hi.searchParams.set('detail', '1');
    modalCard.image_url = `${hi.pathname}${hi.search}`;
  }
  const modal = document.createElement('div');
  modal.id = 'gwent-collection-card-modal';
  modal.className = 'gwent-collection-card-modal';
  modal.setAttribute('role','dialog');
  modal.setAttribute('aria-modal','true');
  modal.setAttribute('aria-label',`Detalhes da carta ${card.nome || ''}`);
  const tags = [
    card.raridade || 'Comum',
    card.faccao || card.tipo || 'Sem facção',
    special ? 'Especial' : (card.row_label || card.fileira || 'Unidade')
  ];
  const combos = Array.isArray(card.combos_compativeis) ? card.combos_compativeis : [];
  const synergies = Array.isArray(card.sinergias) ? card.sinergias : [];
  modal.innerHTML = `
    <section class="gwent-collection-card-dialog">
      <button type="button" class="gwent-collection-close" data-gwent-collection-close aria-label="Fechar">×</button>
      <div class="gwent-collection-art-column">
        <div class="gwent-collection-art">${cardImageMarkup(modalCard, card.nome || 'Carta')}</div>
        <strong class="gwent-collection-card-name">${escapeHTML(card.nome || 'Carta')}</strong>
        <small>EXEMPLAR #${number(card.exemplar_id || 0)}</small>
      </div>
      <div class="gwent-collection-info">
        <header>
          <small class="eyebrow">ARQUIVO DO COLISEU · FICHA DA CARTA</small>
          <h2>${escapeHTML(card.nome || 'Carta')}</h2>
          <div class="gwent-collection-tags">${tags.map(tag=>`<span>${escapeHTML(tag)}</span>`).join('')}</div>
        </header>
        <section class="gwent-collection-power">
          <div><small>PODER-BASE</small><strong>${special ? '—' : number(card.poder)}</strong></div>
          <div><small>PODER MÁXIMO</small><strong>${special ? '—' : number(card.max_power || card.poder)}</strong></div>
          <div><small>POTÊNCIA DA RARIDADE</small><strong>${number(rarityBudget)} / 6</strong></div>
        </section>
        <section class="gwent-collection-section gwent-collection-effect">
          <small>EFEITO DE COMBATE</small>
          <h3>${escapeHTML(abilityName)}</h3>
          <p>${escapeHTML(abilityText)}</p>
        </section>
        ${card.descricao ? `<section class="gwent-collection-section"><small>LORE</small><p class="gwent-collection-lore">${escapeHTML(card.descricao)}</p></section>` : ''}
        ${(synergies.length || combos.length) ? `<section class="gwent-collection-section"><small>SINERGIAS</small>${synergies.length ? `<div class="gwent-collection-chips">${synergies.map(x=>`<span>${escapeHTML(x)}</span>`).join('')}</div>` : ''}${combos.map(x=>`<article class="gwent-collection-combo"><b>${escapeHTML(x.nome || 'Combo')}</b><p>${escapeHTML(x.descricao || '')}</p></article>`).join('')}</section>` : ''}
        <footer class="gwent-collection-actions">
          ${inDeck
            ? `<button type="button" class="secondary" data-gwent-collection-remove="${escapeHTML(card.id)}">REMOVER DO DECK</button>`
            : `<button type="button" class="primary" data-gwent-collection-add="${escapeHTML(card.id)}" ${gwentDeckIds.length >= 12 ? 'disabled' : ''}>ADICIONAR AO DECK</button>`}
          ${canEvolve ? `<button type="button" class="secondary" data-gwent-evolve="${escapeHTML(String(card.exemplar_id))}">EVOLUIR · ${evolveCost} FRAGMENTOS</button>` : ''}
          ${canUpgrade ? `<button type="button" class="secondary" data-gwent-upgrade="${escapeHTML(String(card.exemplar_id))}">LAPIDAR +1 · ${upgradeCost} ALMAS</button>` : ''}
        </footer>
      </div>
    </section>`;
  document.body.appendChild(modal);
  observeCardImages(modal);
  modal.addEventListener('click', event => {
    if (event.target === modal || event.target.closest('[data-gwent-collection-close]')) closeGwentCollectionCardModal();
  });
  modal.querySelector('[data-gwent-collection-close]')?.focus();
}
document.addEventListener('click', event => {
  const inspect = event.target.closest('[data-gwent-inspect]');
  if (inspect) { openGwentCollectionCardModal(inspect.dataset.gwentInspect); return; }
  const add = event.target.closest('[data-gwent-collection-add]');
  if (add) {
    const cardId = add.dataset.gwentCollectionAdd;
    const card = collection.find(item => String(item.id) === String(cardId));
    const selected = gwentDeckIds.map(id => collection.find(item => item.id === id)).filter(Boolean);
    if (gwentDeckIds.length >= 12) return showNotice('O deck já possui 12 cartas.', 'error');
    if (selected.some(item => (item.card_id || item.id) === (card?.card_id || card?.id))) return showNotice('O deck não pode repetir o mesmo modelo.', 'error');
    if (card?.categoria === 'Especial' && selected.filter(item => item.categoria === 'Especial').length >= 4) return showNotice('O deck aceita no máximo quatro cartas especiais.', 'error');
    gwentDeckIds.push(cardId);
    closeGwentCollectionCardModal();
    renderGwentBuilder();
    return;
  }
  const remove = event.target.closest('[data-gwent-collection-remove]');
  if (remove) {
    gwentDeckIds = gwentDeckIds.filter(id => id !== remove.dataset.gwentCollectionRemove);
    closeGwentCollectionCardModal();
    renderGwentBuilder();
  }
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape') closeGwentCollectionCardModal();
});
let atelierPromptText = '';
let atelierNegativeText = '';
let atelierAnalysisText = '';
let atelierPreviewUrl = '';

function renderAtelierCardOptions() {
  const select = $('#atelier-card');
  if (!select) return;
  const models = new Map();
  collection.forEach(card => { const key = card.card_id || card.id; if (!models.has(key)) models.set(key, card); });
  select.innerHTML = '<option value="">Selecione uma carta</option>' + [...models.entries()].map(([key, card]) =>
    `<option value="${escapeHTML(key)}">${escapeHTML(card.nome)} · ${escapeHTML(card.faccao || card.raridade || 'Carta')}</option>`
  ).join('');
}

async function loadAtelierHistory() {
  const target = $('#atelier-history');
  if (!target || !currentUser) return;
  try {
    const response = await fetch('/api/gwent/atelier/history', {credentials:'same-origin', cache:'no-store'});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Não foi possível carregar o histórico do Ateliê.');
    target.innerHTML = (data.history || []).map(item => {
      const labels = {pending:'Em análise', approved:'Aprovada · arte oficial', rejected:'Rejeitada', archived:'Arquivada · não está mais aplicada à carta'};
      return `<article class="atelier-history-item"><b>${escapeHTML(item.card_id)}</b><span>${escapeHTML(labels[item.status] || item.status)}</span><small>${escapeHTML(item.created_at || '')}</small>${item.rejection_reason ? `<p>${escapeHTML(item.rejection_reason)}</p>` : ''}</article>`;
    }).join('') || '<p class="muted">Você ainda não enviou ilustrações.</p>';
  } catch (error) { target.innerHTML = `<p class="muted">${escapeHTML(error.message)}</p>`; }
}

async function loadAtelierReviewQueue() {
  const panel = $('#atelier-review-panel');
  if (!panel || !currentUser) return;
  try {
    const response = await fetch('/api/gwent/atelier/review', {credentials:'same-origin', cache:'no-store'});
    if (response.status === 403) { panel.hidden = true; return; }
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Falha ao consultar a fila.');
    panel.hidden = false;
    await loadAtelierLeaderArtAdmin();
    $('#atelier-review-queue').innerHTML = (data.pending || []).map(item =>
      `<article class="atelier-review-item"><img src="/api/gwent/atelier/submission/${Number(item.id)}/image" alt="Arte submetida"><div><b>${escapeHTML(item.card_id)}</b><small>Artista: ${escapeHTML(item.artist_name || `Discord ${item.user_id}`)}</small><small>${escapeHTML(item.created_at || '')}</small><div class="atelier-review-actions"><button class="primary" type="button" data-atelier-approve="${Number(item.id)}">Aprovar</button><button class="secondary" type="button" data-atelier-reject="${Number(item.id)}">Rejeitar</button></div></div></article>`
    ).join('') || '<p class="muted">Nenhuma arte aguardando aprovação.</p>';
  } catch (error) { panel.hidden = true; showNotice(error.message, 'error'); }
}

let atelierAdminLeaderArts = [];

function selectedAdminLeaderArt() {
  const id = $('#atelier-leader-art-select')?.value || '';
  return atelierAdminLeaderArts.find(item => item.id === id) || null;
}

function updateAtelierLeaderArtPreview() {
  const leader = selectedAdminLeaderArt();
  const preview = $('#atelier-leader-art-preview');
  const empty = $('#atelier-leader-art-empty');
  const remove = $('#atelier-leader-art-remove');
  const upload = $('#atelier-leader-art-upload');
  if (!leader) {
    if (preview) preview.hidden = true;
    if (empty) { empty.hidden = false; empty.textContent = 'Selecione um líder.'; }
    if (remove) remove.hidden = true;
    if (upload) upload.disabled = true;
    return;
  }
  const source = leader.art_url || leader.default_art_url || '';
  if (source && preview) {
    preview.src = source;
    preview.hidden = false;
  } else if (preview) preview.hidden = true;
  if (empty) empty.hidden = !!source;
  if (remove) remove.hidden = !leader.has_art;
  if (upload) upload.disabled = false;
  const status = $('#atelier-leader-art-status');
  if (status) status.textContent = leader.has_art
    ? `Arte personalizada ativa${leader.artist_name ? ` · crédito: ${leader.artist_name}` : ''}. Uma nova imagem substituirá a atual.`
    : 'Retrato padrão em uso. Envie uma imagem para aplicar uma arte personalizada.';
}

async function loadAtelierLeaderArtAdmin() {
  const select = $('#atelier-leader-art-select');
  if (!select) return;
  const response = await fetch('/api/gwent/atelier/leaders', {credentials:'same-origin', cache:'no-store'});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Não foi possível carregar as cartas de líder.');
  atelierAdminLeaderArts = data.leaders || [];
  const previous = select.value;
  select.innerHTML = atelierAdminLeaderArts.map(leader =>
    `<option value="${escapeHTML(leader.id)}">${escapeHTML(leader.name)} · ${escapeHTML(leader.faction)}${leader.has_art ? ' · arte personalizada' : ''}</option>`
  ).join('');
  if (atelierAdminLeaderArts.some(leader => leader.id === previous)) select.value = previous;
  else if (atelierAdminLeaderArts.length) select.value = atelierAdminLeaderArts[0].id;

  const byFaction = {};
  atelierAdminLeaderArts.forEach(leader => {
    if (!byFaction[leader.faction]) byFaction[leader.faction] = [];
    byFaction[leader.faction].push({id:leader.id,name:leader.name,description:leader.description,art_url:leader.art_url,default_art_url:leader.default_art_url});
  });
  applyGwentLeaders(byFaction);
  if ($('#gwent-leader')) renderGwentLeaderOptions($('#gwent-leader').value);
  updateAtelierLeaderArtPreview();
}

async function uploadAtelierLeaderArt() {
  const leader = selectedAdminLeaderArt();
  const file = $('#atelier-leader-art-file')?.files?.[0];
  const status = $('#atelier-leader-art-status');
  const button = $('#atelier-leader-art-upload');
  if (!leader) return;
  if (!file) { if (status) status.textContent = 'Selecione uma imagem antes de aplicar.'; return; }
  const form = new FormData();
  form.append('image', file);
  form.append('artist_name', $('#atelier-leader-art-credit')?.value || '');
  if (button) { button.disabled = true; button.textContent = 'Aplicando arte…'; }
  try {
    const response = await fetch(`/api/gwent/atelier/leaders/${encodeURIComponent(leader.id)}/art`, {
      method:'POST', credentials:'same-origin', body:form
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Não foi possível aplicar a arte ao líder.');
    if (status) status.textContent = `${data.message} ${data.width} × ${data.height}px.`;
    $('#atelier-leader-art-file').value = '';
    await loadAtelierLeaderArtAdmin();
    showNotice(`Arte de ${leader.name} atualizada para todos os jogadores.`, 'success');
  } catch (error) {
    if (status) status.textContent = error.message;
    showNotice(error.message, 'error');
  } finally {
    if (button) { button.disabled = false; button.textContent = 'Aplicar arte ao líder'; }
    updateAtelierLeaderArtPreview();
  }
}

async function removeAtelierLeaderArt() {
  const leader = selectedAdminLeaderArt();
  if (!leader || !leader.has_art) return;
  if (!window.confirm(`Restaurar a arte padrão de ${leader.name}? A imagem personalizada deixará de aparecer na carta de líder.`)) return;
  const button = $('#atelier-leader-art-remove');
  if (button) { button.disabled = true; button.textContent = 'Restaurando…'; }
  try {
    const response = await fetch(`/api/gwent/atelier/leaders/${encodeURIComponent(leader.id)}/art`, {
      method:'DELETE', credentials:'same-origin', headers:{'Content-Type':'application/json'}
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Não foi possível restaurar a arte padrão.');
    await loadAtelierLeaderArtAdmin();
    showNotice(`Retrato padrão de ${leader.name} restaurado.`, 'success');
  } catch (error) {
    const status = $('#atelier-leader-art-status');
    if (status) status.textContent = error.message;
    showNotice(error.message, 'error');
  } finally {
    if (button) { button.disabled = false; button.textContent = 'Restaurar arte padrão'; }
  }
}

async function removeAllAtelierArts() {
  const confirmed = window.confirm(
    'Remover todas as artes oficiais atualmente aplicadas às cartas?\n\n' +
    'As cartas voltarão à arte-base. O histórico, os créditos dos artistas e os arquivos enviados serão preservados. Esta ação não pode ser desfeita pelo site.'
  );
  if (!confirmed) return;
  const button = $('#atelier-remove-all-art');
  if (button) { button.disabled = true; button.textContent = 'Removendo artes...'; }
  try {
    const response = await fetch('/api/gwent/atelier/remove-all-art', {
      method: 'POST', credentials: 'same-origin',
      headers: {'Content-Type': 'application/json'}, body: '{}'
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Não foi possível remover as artes oficiais.');
    await Promise.all([loadAtelierHistory(), loadAtelierOfficialArt()]);
    const cards = Number(data.cartas_limpas || 0);
    const arts = Number(data.artes_removidas || 0);
    showNotice(`${arts} arte(s) retirada(s) de ${cards} carta(s). Histórico e arquivos preservados.`, 'success');
  } catch (error) {
    showNotice(error.message, 'error');
  } finally {
    if (button) { button.disabled = false; button.textContent = 'Remover todas as artes aplicadas'; }
  }
}

async function loadAtelier() {
  if (!currentUser) return;
  renderAtelierCardOptions();
  await Promise.all([loadAtelierHistory(), loadAtelierReviewQueue(), loadAtelierOfficialArt()]);
}

async function loadAtelierOfficialArt() {
  const cardId = $('#atelier-card')?.value;
  const target = $('#atelier-official-art');
  if (!target) return;
  if (!cardId) { target.innerHTML = '<p class="muted">Selecione uma carta para verificar a arte oficial.</p>'; return; }
  try {
    const response = await fetch(`/api/gwent/atelier/official/${encodeURIComponent(cardId)}`, {credentials:'same-origin', cache:'no-store'});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Falha ao consultar arte oficial.');
    target.innerHTML = data.official
      ? `<img class="atelier-official-preview" src="${escapeHTML(data.image_url)}" alt="Arte oficial comunitária"><small>Arte oficial por <b>${escapeHTML(data.artist_name)}</b> · ${escapeHTML(data.created_at)}</small>`
      : '<p class="muted">Esta carta ainda utiliza a arte-base. Sua submissão pode se tornar a primeira arte oficial.</p>';
  } catch (error) { target.innerHTML = `<p class="muted">${escapeHTML(error.message)}</p>`; }
}

async function generateAtelierPrompt() {
  const cardId = $('#atelier-card').value;
  if (!cardId) return showNotice('Selecione uma carta da sua coleção.', 'error');
  const button = $('#atelier-generate-prompt'); button.disabled = true;
  try {
    const response = await fetch(`/api/gwent/atelier/prompt?card_id=${encodeURIComponent(cardId)}`, {credentials:'same-origin', cache:'no-store'});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Não foi possível gerar o prompt.');
    atelierPromptText = data.prompt || '';
    atelierNegativeText = data.negative_prompt || '';
    atelierAnalysisText = data.analysis || '';
    $('#atelier-analysis').value = atelierAnalysisText;
    $('#atelier-prompt').value = atelierPromptText;
    $('#atelier-negative').value = atelierNegativeText;
    $('#atelier-copy-prompt').disabled = !atelierPromptText;
    $('#atelier-copy-negative').disabled = !atelierNegativeText;
    $('#atelier-copy-bundle').disabled = !(atelierAnalysisText && atelierPromptText && atelierNegativeText);
    showNotice(`Direção de arte e prompts gerados para ${data.name} · formato ${data.aspect_ratio || '5:4'}.`, 'success');
  } catch (error) { showNotice(error.message, 'error'); }
  finally { button.disabled = false; }
}

async function submitAtelierArt() {
  const cardId = $('#atelier-card').value;
  const file = $('#atelier-image').files?.[0];
  if (!cardId || !file) return showNotice('Selecione a carta e a imagem.', 'error');
  if (!atelierPromptText) return showNotice('Gere o prompt individual da carta antes de enviar.', 'error');
  if (file.size > 8 * 1024 * 1024) return showNotice('A imagem ultrapassa o limite de 8 MB.', 'error');
  const form = new FormData(); form.append('card_id', cardId); form.append('prompt_text', `A. ANÁLISE ARTÍSTICA\n${atelierAnalysisText}\n\nB. PROMPT PROFISSIONAL\n${atelierPromptText}\n\nC. NEGATIVE PROMPT\n${atelierNegativeText}`); form.append('artist_name', ($('#atelier-artist-name').value || '').trim()); form.append('image', file);
  const button = $('#atelier-submit'); button.disabled = true;
  try {
    const response = await fetch('/api/gwent/atelier/submit', {method:'POST', credentials:'same-origin', body:form});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Não foi possível enviar a ilustração.');
    showNotice(`Ilustração enviada para aprovação · submissão #${data.submission_id}.`, 'success');
    $('#atelier-image').value = ''; $('#atelier-preview').hidden = true;
    await loadAtelierHistory(); await loadAtelierReviewQueue();
  } catch (error) { showNotice(error.message, 'error'); }
  finally { button.disabled = false; }
}

async function decideAtelierSubmission(id, approve) {
  document.querySelectorAll('[data-atelier-approve],[data-atelier-reject]').forEach(b => b.disabled = true);
  let reason = '';
  if (!approve) { reason = window.prompt('Informe o motivo da rejeição (opcional):', '') ?? null; if (reason === null) { await loadAtelierReviewQueue(); return; } }
  try {
    const response = await fetch(`/api/gwent/atelier/review/${id}`, {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'}, body:JSON.stringify({approve, reason})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Não foi possível registrar a decisão.');
    showNotice(approve ? 'Arte aprovada e publicada como ilustração oficial.' : 'Arte rejeitada; o motivo foi registrado.', 'success');
    await loadAtelierReviewQueue();
    await loadAtelierOfficialArt();
  } catch (error) { showNotice(error.message, 'error'); await loadAtelierReviewQueue(); }
}

async function loadGwentStore() {
  if (!currentUser) return;
  const status = $('#gwent-store-status');
  try {
    const response = await fetch('/api/gwent/store', {credentials:'same-origin', cache:'no-store'});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Não foi possível carregar o mercado.');
    const pack = data.pack || {};
    $('#gwent-store-wallet').textContent = `${number(data.summary?.denarios)} Denários disponíveis`;
    $('#gwent-pack-limit').textContent = `${number(pack.remaining)} de ${number(pack.daily_limit || 3)} pacotes restantes nas próximas 24 horas.`;
    const button = $('#gwent-open-pack');
    button.disabled = !pack.available || Number(data.summary?.denarios || 0) < Number(pack.price || 120);
    button.textContent = Number(data.summary?.denarios || 0) < Number(pack.price || 120)
      ? 'Denários insuficientes' : `Abrir por ${number(pack.price || 120)} Denários`;
    if (status) status.textContent = `Cada pacote contém ${number(pack.cards || 3)} cartas. Duplicatas geram recursos; a coleção é compartilhada com os drops.`;
  } catch (error) { if (status) status.textContent = error.message; }
}

async function buyGwentPack() {
  const button = $('#gwent-open-pack');
  if (!button || button.disabled || !currentUser) return;
  if (!window.confirm('Comprar um pacote com 3 cartas por 120 Denários?')) return;
  button.disabled = true;
  const status = $('#gwent-store-status');
  try {
    const response = await fetch('/api/gwent/store/pack', {
      method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'}, body:JSON.stringify({})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Não foi possível comprar o pacote.');
    const cards = Array.isArray(data.cards) ? data.cards : [];
    $('#gwent-pack-results').innerHTML = `<div class="gwent-pack-opened"><h4>Pacote aberto</h4><div class="gwent-pack-opened-cards">${cards.map(card => `<article class="pk" data-r="${escapeHTML(String(card.rarity||'comum').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,''))}"><b>${escapeHTML(card.card_name || card.card_id)}</b><span>${escapeHTML(card.rarity)} · ${number(card.power)} poder</span><small>${card.outcome === 'carta' ? 'Novo exemplar' : card.outcome === 'almas' ? `Duplicata · +${number(card.almas)} Almas` : `Duplicata · +${number(card.fragmentos)} fragmentos`}</small></article>`).join('')}</div></div>`;
    revealPack();
    showNotice('Pacote comprado e aberto. As cartas já estão na sua coleção.', 'success');
    await loadAccount(); await loadGwentStore(); await loadDropHistory();
  } catch (error) {
    showNotice(error.message, 'error');
    if (status) status.textContent = error.message;
    await loadGwentStore();
  }
}

async function loadDropHistory() {
  const target = $('#gwent-drop-history');
  if (!target || !currentUser) return;
  try {
    const response = await fetch('/api/gwent/drops/history', {credentials:'same-origin', cache:'no-store'});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Não foi possível carregar o histórico.');
    const history = Array.isArray(data.history) ? data.history : [];
    const movements = Array.isArray(data.movements) ? data.movements : [];
    const entries = [
      ...history.map(item => ({...item, entry_type:'drop'})),
      ...movements.map(item => ({...item, entry_type:'movement'})),
    ].sort((a,b) => String(b.created_at || '').localeCompare(String(a.created_at || '')));
    target.innerHTML = entries.map(item => {
      if (item.entry_type === 'movement') {
        const evolved = item.action === 'evolucao';
        const title = evolved ? 'Carta evoluída' : 'Carta lapidada';
        const detail = evolved
          ? `${item.rarity_before} → ${item.rarity_after} · -${number(item.amount)} fragmentos`
          : `${item.rarity_after} · ${number(item.power_before)} → ${number(item.power_after)} poder · -${number(item.amount)} Almas`;
        return `<article class="gwent-drop-history-item"><div><b>${escapeHTML(title)}</b><small>${escapeHTML(item.card_name || item.card_id || 'Carta')} · ${escapeHTML(detail)}</small></div><strong>#${number(item.exemplar_id)}</strong></article>`;
      }
      const outcome = item.outcome === 'revertido' ? 'Recompensa revertida'
        : item.outcome === 'almas' ? `Duplicata · +${number(item.almas_delta)} Almas`
        : item.outcome === 'fragmentos' ? `Duplicata · +${number(item.fragmentos_delta)} fragmentos`
        : item.outcome === 'singular' ? 'Feito especial · Singular conquistada'
        : item.outcome === 'singular_ja_possui' ? 'Feito especial · Singular já conquistada'
        : 'Carta adicionada à coleção';
      const sourceNames = {zerado:'Jogo zerado', platina:'Platina', run:'Run Soulslike', comunidade:'Comunidade', port:'Port enviado', mod:'Mod enviado', boas_vindas:'Boas-vindas', patente:'Patente', feito_singular:'Feito especial'};
      const source = sourceNames[item.origin] || (item.origin ? item.origin.replaceAll('_', ' ') : 'Atividade');
      return `<article class="gwent-drop-history-item"><div><b>${escapeHTML(item.card_name || 'Carta')}</b><small>${escapeHTML(item.rarity || 'Comum')} · ${escapeHTML(outcome)} · ${escapeHTML(source)}</small></div><strong>${item.power ? `${number(item.power)} poder` : ''}</strong></article>`;
    }).join('') || '<p class="muted">Ainda não há movimentações registradas.</p>';
  } catch (error) { target.innerHTML = `<p class="muted">${escapeHTML(error.message)}</p>`; }
}

async function loadGwentDeck() {
  if (!currentUser) return;
  try {
    const r = await fetch('/api/gwent/deck', {credentials:'same-origin', cache:'no-store'});
    const data = await parseGwentApiResponse(r);
    if (!r.ok) throw new Error(data.error || 'Não foi possível carregar o deck Gwent.');
    gwentSavedIds = (data.deck || []).map(c => c.id);
    gwentDeckIds = [...gwentSavedIds];
    gwentSavedFaction = data.faction || 'Ordem Áurea';
    gwentSavedLeader = data.leader_id || 'comandante_fornalha';
    gwentSavedRelic = data.relic_id || '';
    const relicSelect = $('#gwent-relic-select');
    if (relicSelect) { relicSelect.value = gwentSavedRelic; relicSelect.dispatchEvent(new Event('change', {bubbles:true})); }
    applyGwentLeaders(data.leaders_by_faction);
    $('#gwent-faction').value = gwentSavedFaction;
    renderGwentLeaderOptions(gwentSavedLeader);
    $('#gwent-deck-status').textContent = gwentSavedIds.length === 12 ? 'Deck carregado.' : 'Monte seu deck Gwent com 12 cartas únicas para liberar a arena.';
    renderGwentBuilder();
  } catch (e) { $('#gwent-deck-status').textContent = e.message; }
}

async function saveGwentDeck() {
  const button = $('#gwent-save-deck'); button.disabled = true; button.textContent = 'Salvando...';
  try {
    const r = await fetch('/api/gwent/deck', {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'}, body:JSON.stringify({cards:gwentDeckIds.map(key => { const card = collection.find(c => c.id === key); return {card_id:card?.card_id || card?.id, exemplar_id:Number(card?.exemplar_id || 0)}; }), faction:$('#gwent-faction').value, leader_id:$('#gwent-leader').value, relic_id:$('#gwent-relic-select')?.value || ''})});
    const data = await parseGwentApiResponse(r); if (!r.ok) throw new Error(data.error || 'Falha ao salvar deck.');
    gwentSavedIds = [...gwentDeckIds]; gwentSavedFaction = $('#gwent-faction').value; gwentSavedLeader = $('#gwent-leader').value; gwentSavedRelic = $('#gwent-relic-select')?.value || '';
    $('#gwent-deck-status').textContent = 'Deck, facção e líder salvos. Seu exército está pronto para a arena.';
    showNotice('Deck Gwent atualizado.', 'success');
  } catch(e) { $('#gwent-deck-status').textContent = e.message; }
  finally { button.textContent = 'Salvar deck Gwent'; renderGwentBuilder(); }
}

async function resetGwentDeck() {
  if (!window.confirm('Redefinir seu deck Gwent? Todas as 12 posições e a configuração de facção, líder e relíquia serão zeradas. Suas cartas continuarão na coleção.')) return;
  const button = $('#gwent-reset-deck');
  if (button) { button.disabled = true; button.textContent = 'Zerando...'; }
  try {
    const response = await fetch('/api/gwent/deck/reset', {
      method: 'POST', credentials: 'same-origin',
      headers: {'Content-Type': 'application/json'}, body: '{}'
    });
    const data = await parseGwentApiResponse(response);
    if (!response.ok) throw new Error(data.error || 'Não foi possível redefinir o deck.');
    try { localStorage.removeItem('narabot_gwent_relic_loadout_v20'); } catch (_) {}
    const relic = $('#gwent-relic-select');
    if (relic) {
      relic.value = '';
      relic.dispatchEvent(new Event('change', {bubbles: true}));
    }
    await loadGwentDeck();
    showNotice('Deck zerado. Suas cartas continuam disponíveis na coleção.', 'success');
  } catch (error) {
    $('#gwent-deck-status').textContent = error.message;
    showNotice(error.message, 'error');
  } finally {
    if (button) button.textContent = 'Redefinir deck';
    renderGwentBuilder();
  }
}

async function loadGwentMatches() {
  if (!currentUser) return;
  try {
    const r = await fetch('/api/gwent/matches', {credentials:'same-origin', cache:'no-store'}); const data = await r.json();
    if (!r.ok) throw new Error(data.error || 'Falha ao carregar partidas.');
    const rank = data.ranking || {mmr:1000,wins:0,losses:0,draws:0,tier:'Bronze'};
    const leaderboard = `<article class="duel-item gwent-leaderboard"><div><small class="eyebrow">TOP 10 DO SERVIDOR</small><h3>Classificação</h3><p>${(data.leaderboard || []).map((p,i) => `${i+1}. ${escapeHTML(p.name)} — ${number(p.mmr)} MMR`).join('<br>') || 'Ainda sem partidas ranqueadas.'}</p></div></article>`;
    const matchCards = (data.matches || []).map(m => {
      const isCreator = m.creator_id === String(currentUser.id);
      const isAI = Boolean(m.is_ai_match) || String(m.opponent_id) === '-1';
      const role = isAI ? 'Modo solo · Adversária: NARA IA' : (isCreator ? 'Você enviou o convite' : 'Você recebeu o convite');
      if (m.status === 'pending') {
        const controls = isCreator
          ? '<span class="muted">Aguardando resposta</span><button class="secondary" data-gwent-respond="cancel" data-match-id="' + m.id + '">Cancelar convite</button>'
          : '<button class="primary" data-gwent-respond="accept" data-match-id="' + m.id + '">Aceitar</button><button class="secondary" data-gwent-respond="decline" data-match-id="' + m.id + '">Recusar</button>';
        return `<article class="duel-item"><div><small class="eyebrow">CONVITE #${number(m.id)}</small><h3>Desafio aguardando resposta</h3><p>${role} · ${escapeHTML(m.created_at || '')}</p></div><div class="duel-controls">${controls}</div></article>`;
      }
      if (m.status === 'active') return `<article class="duel-item ${isAI ? 'gwent-ai-match' : ''}"><div><small class="eyebrow">GWENT #${number(m.id)}${isAI ? ' · TREINO' : ''}</small><h3>${isAI ? 'Treino contra NARA' : 'Partida em andamento'}</h3><p>${role} · ${escapeHTML(m.created_at || '')}</p></div><button class="primary" data-gwent-open="${m.id}">${isAI ? 'Continuar treino' : 'Abrir arena'}</button></article>`;
      const statusLabel = isAI ? 'Treino contra NARA · Finalizado' : (m.status === 'finished' ? 'Finalizada' : m.status === 'declined' ? 'Convite recusado' : m.status === 'cancelled' ? 'Convite cancelado' : 'Partida encerrada');
      return `<article class="duel-item ${isAI ? 'gwent-ai-match' : ''}"><div><small class="eyebrow">GWENT #${number(m.id)}${isAI ? ' · TREINO' : ''}</small><h3>${statusLabel}</h3><p>${role} · ${escapeHTML(m.created_at || '')}</p></div>${m.status === 'finished' ? `<button class="secondary" data-gwent-open="${m.id}">Ver resultado</button>` : ''}</article>`;
    }).join('');
    $('#gwent-match-list').innerHTML = `<article class="duel-item gwent-rank"><div><small class="eyebrow">SEU RANKING</small><h3>${escapeHTML(rank.tier)} · ${number(rank.mmr)} MMR</h3><p>${number(rank.wins)} vitórias · ${number(rank.losses)} derrotas · ${number(rank.draws)} empates</p></div><span>MMR Elo variável por resultado</span></article>` + leaderboard + (matchCards || '<div class="empty-state">Nenhuma partida Gwent registrada.</div>');
  } catch(e) { $('#gwent-match-list').innerHTML = `<div class="empty-state">${escapeHTML(e.message)}</div>`; }
}

async function createGwentMatch() {
  const opponent_id = $('#gwent-opponent').value;
  if (!opponent_id) return showNotice('Selecione um adversário.', 'error');
  if (gwentSavedIds.length !== 12) return showNotice('Salve primeiro um deck Gwent com 12 cartas.', 'error');
  const button = $('#gwent-create-match'); button.disabled = true;
  try {
    const r = await fetch('/api/gwent/matches', {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'}, body:JSON.stringify({opponent_id})});
    const data = await r.json(); if (!r.ok) throw new Error(data.error || 'Não foi possível iniciar partida.');
    showNotice('Convite enviado. A partida só começa quando o adversário aceitar.', 'success');
    await loadGwentMatches();
  } catch(e) { showNotice(e.message, 'error'); }
  finally { button.disabled = false; }
}


async function createGwentSoloMatch() {
  if (gwentSavedIds.length !== 12) return showNotice('Salve primeiro um deck Gwent com 12 cartas.', 'error');
  const button = $('#gwent-solo-match');
  if (!button) return;
  button.disabled = true;
  const originalText = button.textContent;
  button.textContent = 'Preparando adversária…';
  try {
    const response = await fetch('/api/gwent/matches/solo', {
      method: 'POST', credentials: 'same-origin',
      headers: {'Content-Type': 'application/json'}, body: JSON.stringify({difficulty: 'normal'})
    });
    const data = await parseGwentApiResponse(response);
    if (!response.ok) throw new Error(data.error || 'Não foi possível iniciar o treino contra a NARA.');
    showNotice('A NARA está pronta. Boa partida.', 'success');
    await loadGwentMatches();
    await openGwentMatch(data.match_id);
  } catch (error) {
    showNotice(error.message || 'Falha ao iniciar partida solo.', 'error');
  } finally {
    button.disabled = false;
    button.textContent = originalText;
  }
}

function gwentEffectivePower(card, weatherValue = 0) {
  const weatherPenalty = Math.max(0, Number(weatherValue || 0) - Number(card.weather_resist || 0));
  const statusPenalty = Math.min(3,
    Number(card.geada || 0) + Number(card.podrida || 0) + Number(card.loucura || 0)
  );
  return Math.max(1, Number(card.poder || 0) + Number(card.bonus || 0) - weatherPenalty - statusPenalty);
}
function gwentCardView(card, isEntering = false, weatherValue = 0) {
  const power = gwentEffectivePower(card, weatherValue);
  const statuses = [
    ['sangramento', '🩸', 'Sangramento'],
    ['geada', '❄️', 'Geada'],
    ['podrida', '🌺', 'Podridão Escarlate'],
    ['loucura', '🔥', 'Loucura']
  ].filter(([key]) => Number(card[key] || 0) > 0)
    .map(([key, glyph, label]) => `<i class="gwent-status" title="${label} ×${number(card[key])}">${glyph}</i>`).join('');
  const title = `${card.nome || 'Carta'} · ${power} poder efetivo · ${card.row_label || ''}${Number(card.escudo || 0) > 0 ? ' · Escudo' : ''}`;
  return `<article class="gwent-board-card ${isEntering ? 'is-entering' : ''}" data-card-id="${escapeHTML(card.id)}" data-row="${escapeHTML(card.row || '')}" role="button" tabindex="0" aria-label="Inspecionar ${escapeHTML(card.nome || 'carta')}, ${power} de poder efetivo" title="${escapeHTML(title)}">${cardImageMarkup(card, card.nome || 'Carta')}<span class="gwent-board-power">${power}</span><span class="gwent-statuses">${statuses}</span>${Number(card.escudo || 0) > 0 ? '<i class="gwent-shield" title="Escudo">◆</i>' : ''}</article>`;
}

let gwentAlvos = {};
let gwentBoardCardsById = new Map();
const gwentRowLabel = (key) => (gwentRows.find(([k]) => k === key) || [key, key])[1];
function gwentOpcoesDoAlvo(cardId, row) {
  const info = gwentAlvos[cardId];
  if (!info) return null;
  const opcoes = (info.opcoes || []).filter(o => info.filtro_fileira === 'mesma' ? o.row === row
    : info.filtro_fileira === 'diferente' ? o.row !== row : true);
  return {...info, opcoes};
}
function closeGwentTargetPicker() { document.getElementById('gwent-target-modal')?.remove(); }
function openGwentTargetPicker(cardId, row, info) {
  closeGwentTargetPicker();
  const modal = document.createElement('div');
  modal.id = 'gwent-target-modal'; modal.className = 'gwent-target-modal';
  modal.setAttribute('role', 'dialog'); modal.setAttribute('aria-modal', 'true');
  modal.innerHTML = `<div class="gwent-target-box"><h3>${escapeHTML(info.rotulo || 'Escolha o alvo')}</h3><div class="gwent-target-list">${
    info.opcoes.map(o => `<button type="button" class="gwent-target-option" data-gwent-target="${escapeHTML(o.id)}"><b>${escapeHTML(o.nome)}</b><small>${number(o.poder + o.bonus)} poder · ${escapeHTML(gwentRowLabel(o.row))}${o.escudo > 0 ? ' · Escudo' : ''}</small></button>`).join('')
  }</div><div class="gwent-target-actions"><button type="button" class="secondary" data-gwent-target="">Automático</button><button type="button" class="secondary" data-gwent-target-cancel>Cancelar</button></div></div>`;
  modal.addEventListener('click', ev => {
    if (ev.target === modal || ev.target.closest('[data-gwent-target-cancel]')) return closeGwentTargetPicker();
    const choice = ev.target.closest('[data-gwent-target]');
    if (!choice) return;
    closeGwentTargetPicker();
    sendGwentAction('play', cardId, row, [], choice.dataset.gwentTarget || '');
  });
  document.addEventListener('keydown', function onEsc(ev) {
    if (ev.key === 'Escape') { closeGwentTargetPicker(); document.removeEventListener('keydown', onEsc); }
  });
  document.body.appendChild(modal);
  modal.querySelector('button')?.focus();
}

function closeGwentRelicPicker() { document.getElementById('gwent-relic-modal')?.remove(); }
function openGwentRelicPicker(data = currentGwentData) {
  if (!data || !data.is_your_turn || data.phase !== 'battle') return;
  const relicId = String(data.equipped_relic_id || '');
  if (!relicId || data.relic_used) return;
  const mine = data.score?.[String(data.your_id)] || {};
  const enemyId = String(data.opponent?.id || '');
  const enemy = data.score?.[enemyId] || {};
  const needsRow = ['reliquia_noite_chama','reliquia_lamina_negra','reliquia_algemas_margit'].includes(relicId);
  const needsTarget = ['reliquia_lamina_negra','reliquia_algemas_margit'].includes(relicId);
  const rowLabels = {melee:'Corpo a corpo',ranged:'Longa distância',siege:'Cerco'};
  const rowKeys = ['melee','ranged','siege'];
  const firstRow = rowKeys.find(row => (enemy.board || []).some(unit => unit.row === row)) || 'melee';
  const modal = document.createElement('div');
  modal.id = 'gwent-relic-modal'; modal.className = 'gwent-target-modal';
  modal.setAttribute('role','dialog'); modal.setAttribute('aria-modal','true');
  const relicNames = {
    reliquia_grande_runa_godrick:'Grande Runa de Godrick', reliquia_runa_nao_nascidos:'Grande Runa dos Não Nascidos',
    reliquia_runa_morte:'Runa da Morte', reliquia_noite_chama:'Espada da Noite e da Chama',
    reliquia_lamina_negra:'Lâmina Negra', reliquia_algemas_margit:'Algemas de Margit'
  };
  modal.innerHTML = `<div class="gwent-target-box"><small class="eyebrow">AÇÃO ÚNICA DA PARTIDA</small><h3>${escapeHTML(relicNames[relicId] || 'Relíquia')}</h3>
    ${needsRow ? `<label class="gwent-relic-choice"><span>FILEIRA INIMIGA</span><select id="gwent-relic-row">${rowKeys.map(row => `<option value="${row}" ${row === firstRow ? 'selected' : ''}>${rowLabels[row]}</option>`).join('')}</select></label>` : ''}
    ${relicId === 'reliquia_noite_chama' ? `<label class="gwent-relic-choice"><span>POSTURA</span><select id="gwent-relic-mode"><option value="noite">Noite — aplicar Geada à fileira</option><option value="chama">Chama — atingir a unidade mais forte</option></select></label>` : ''}
    ${needsTarget ? `<label class="gwent-relic-choice"><span>ALVO</span><select id="gwent-relic-target"></select></label>` : ''}
    <p class="muted">A ativação consome seu turno. A Relíquia só pode ser consumida uma vez por partida.</p>
    <div class="gwent-target-actions"><button type="button" data-gwent-relic-confirm>CONFIRMAR</button><button type="button" class="secondary" data-gwent-relic-cancel>CANCELAR</button></div></div>`;
  const updateTargets = () => {
    if (!needsTarget) return;
    const row = modal.querySelector('#gwent-relic-row')?.value || firstRow;
    const targetSelect = modal.querySelector('#gwent-relic-target');
    const targets = (enemy.board || []).filter(unit => unit.row === row);
    targetSelect.innerHTML = targets.map(unit => `<option value="${escapeHTML(unit.id)}">${escapeHTML(unit.nome)} · ${number(Math.max(1, Number(unit.poder || 0) + Number(unit.bonus || 0)))} poder${Number(unit.escudo || 0) > 0 ? ' · Escudo' : ''}</option>`).join('');
    modal.querySelector('[data-gwent-relic-confirm]').disabled = !targets.length;
  };
  modal.addEventListener('change', event => { if (event.target.id === 'gwent-relic-row') updateTargets(); });
  modal.addEventListener('click', event => {
    if (event.target === modal || event.target.closest('[data-gwent-relic-cancel]')) return closeGwentRelicPicker();
    if (!event.target.closest('[data-gwent-relic-confirm]')) return;
    const row = modal.querySelector('#gwent-relic-row')?.value || '';
    const target = needsTarget ? (modal.querySelector('#gwent-relic-target')?.value || '')
      : relicId === 'reliquia_noite_chama' ? (modal.querySelector('#gwent-relic-mode')?.value || 'noite') : '';
    closeGwentRelicPicker();
    sendGwentAction('relic', '', row, [], target);
  });
  document.body.appendChild(modal);
  updateTargets();
  modal.querySelector('select')?.focus();
}

function replaceGwentArenaMarkup(arena, markup) {
  // Reusa os próprios elementos <img> que já carregaram. Substituir o HTML
  // completo sem isso faz o navegador piscar/reabrir todas as artes a cada jogada.
  const reusableImages = new Map();
  arena.querySelectorAll('img[data-card-src]').forEach(image => {
    const key = image.dataset.cardSrc || '';
    if (!key) return;
    if (!reusableImages.has(key)) reusableImages.set(key, []);
    reusableImages.get(key).push(image);
  });

  // Mantém escolhas locais caso o adversário faça uma jogada enquanto o usuário
  // está marcando cartas da troca inicial ou selecionando uma fileira.
  const checkedSwapIds = new Set([...arena.querySelectorAll('[data-gwent-swap]:checked')].map(el => el.value));
  const selectedRows = new Map([...arena.querySelectorAll('select[data-gwent-row]')].map(el => [el.dataset.gwentRow, el.value]));
  const selectedActionRow = arena.querySelector('#gwent-selected-row')?.value || '';
  const focused = document.activeElement && arena.contains(document.activeElement) ? document.activeElement : null;
  let focusInfo = null;
  if (focused) {
    if (focused.id) focusInfo = {id: focused.id};
    else {
      const attr = ['data-gwent-swap', 'data-gwent-row', 'data-gwent-play', 'data-gwent-select-card', 'data-gwent-pass', 'data-gwent-leader', 'data-gwent-weather', 'data-gwent-keep', 'data-gwent-mulligan', 'data-gwent-surrender', 'data-gwent-relic', 'data-gwent-hand-toggle'].find(name => focused.hasAttribute(name));
      if (attr) focusInfo = {attr, value: attr === 'data-gwent-swap' ? focused.value : focused.getAttribute(attr)};
    }
  }

  const template = document.createElement('template');
  template.innerHTML = markup;
  template.content.querySelectorAll('img[data-card-src]').forEach(nextImage => {
    const key = nextImage.dataset.cardSrc || '';
    const list = reusableImages.get(key);
    const previousImage = list && list.length ? list.shift() : null;
    if (previousImage) {
      previousImage.alt = nextImage.alt;
      nextImage.replaceWith(previousImage);
    }
  });
  template.content.querySelectorAll('[data-gwent-swap]').forEach(el => {
    if (checkedSwapIds.has(el.value) && !el.disabled) el.checked = true;
  });
  template.content.querySelectorAll('select[data-gwent-row]').forEach(el => {
    const prior = selectedRows.get(el.dataset.gwentRow);
    if (prior && [...el.options].some(option => option.value === prior)) el.value = prior;
  });
  const nextActionRow = template.content.querySelector('#gwent-selected-row');
  if (nextActionRow && selectedActionRow && [...nextActionRow.options].some(option => option.value === selectedActionRow)) nextActionRow.value = selectedActionRow;

  const scrollX = window.scrollX;
  const scrollY = window.scrollY;
  arena.replaceChildren(template.content);

  if (focusInfo) {
    let target = focusInfo.id ? arena.querySelector(`#${CSS.escape(focusInfo.id)}`) : null;
    if (!target && focusInfo.attr) {
      target = [...arena.querySelectorAll(`[${focusInfo.attr}]`)].find(el =>
        (focusInfo.attr === 'data-gwent-swap' ? el.value : el.getAttribute(focusInfo.attr)) === focusInfo.value
      ) || null;
    }
    try { target?.focus({preventScroll:true}); } catch { /* foco é apenas preservado quando suportado */ }
  }

  // Se o navegador ainda ajustar a âncora da página durante a troca do DOM,
  // restaura a posição sem animação. Não força scroll quando nada se moveu.
  if (Math.abs(window.scrollY - scrollY) > 1 || Math.abs(window.scrollX - scrollX) > 1) {
    const root = document.documentElement;
    const oldBehavior = root.style.scrollBehavior;
    root.style.scrollBehavior = 'auto';
    window.scrollTo(scrollX, scrollY);
    root.style.scrollBehavior = oldBehavior;
  }
}

function renderGwentArena(data) {
  currentGwentData = data;
  const arena = $('#gwent-arena');
  // O modo de duelo é aplicado no ponto de renderização também: protege contra
  // fluxos que abrem uma partida sem passar pelo botão padrão de entrada.
  document.body.classList.add('gwent-match-active');
  document.documentElement.classList.add('gwent-match-active');
  arena.hidden = false;
  gwentAlvos = data.alvos || {};
  if (!data.is_your_turn) closeGwentTargetPicker();

  const score = data.score || {};
  const ids = Object.keys(score);
  const my = String(data.your_id || '');
  const enemy = ids.find(id => String(id) !== my);
  const mine = score[my] || {board:[], score:0, crowns:0, hand:0, passed:false};
  const theirs = score[enemy] || {board:[], score:0, crowns:0, hand:0, passed:false};
  gwentBoardCardsById = new Map([...(mine.board || []), ...(theirs.board || [])].map(card => [String(card.id), card]));
  const opponentName = data.opponent?.name || `Jogador ${String(enemy || '').slice(-4)}`;
  const winnerLabel = data.winner_id
    ? (String(data.winner_id) === my ? 'Você venceu' : `${opponentName} venceu`)
    : 'Empate';
  const prep = data.phase === 'mulligan';
  const hand = Array.isArray(data.hand) ? data.hand : [];
  gwentHandCardsById = new Map(hand.map(card => [String(card.id), card]));
  if (gwentSelectedHandCard && !gwentHandCardsById.has(String(gwentSelectedHandCard))) gwentSelectedHandCard = '';
  const handPhase = prep ? 'prep' : data.status === 'finished' ? 'finished' : data.is_your_turn ? 'mine' : 'enemy';
  if (handPhase !== gwentHandLastPhase) {
    gwentHandOpen = null;
    gwentHandLastPhase = handPhase;
    gwentSelectedHandCard = '';
  }
  const handIsOpen = gwentHandOpen === null ? (prep || (data.is_your_turn && hand.length > 0)) : gwentHandOpen;
  arena.classList.toggle('hand-open', handIsOpen);

  const cardsAlreadyOnBoard = new Set(
    [...arena.querySelectorAll('.gwent-board-card[data-card-id]')].map(card => String(card.dataset.cardId))
  );
  const board = (side, mirrored = false) => (mirrored ? [...gwentRows].reverse() : gwentRows).map(([key,label]) => {
    const cards = (side.board || []).filter(card => card.row === key);
    const rowPower = cards.reduce((total, card) => total + Math.max(
      1,
      gwentEffectivePower(card, Number((data.weather && data.weather[key]) || 0))
    ), 0);
    const hasEnteringCard = cards.some(card => !cardsAlreadyOnBoard.has(String(card.id)));
    return `<div class="gwent-row ${hasEnteringCard ? 'has-entering' : ''}" data-row="${escapeHTML(key)}" data-card-count="${cards.length}" style="--row-card-count:${Math.max(1, cards.length)};--row-card-height:${Math.max(112, 238 - Math.max(0, cards.length - 1) * 18)}px">
      <h4><span>${escapeHTML(label)}</span><b>${number(rowPower)}</b></h4>
      <div class="gwent-board-cards">${cards.map(card => gwentCardView(card, !cardsAlreadyOnBoard.has(String(card.id)), Number((data.weather && data.weather[key]) || 0))).join('')}</div>
    </div>`;
  }).join('');

  const eventHistory = Array.isArray(data.event_log) ? data.event_log : [];
  const eventPanel = `<details class="gwent-history"><summary>Histórico · ${number(eventHistory.length)}</summary><ol>${eventHistory.slice().reverse().map(item => `<li>${escapeHTML(item)}</li>`).join('') || '<li>A partida ainda não possui jogadas registradas.</li>'}</ol></details>`;
  const reward = data.reward;
  const rewardPanel = data.status === 'finished' && reward
    ? `<aside class="gwent-reward-panel"><b>Recompensas</b><span>+${number(reward.reward_xp)} XP · +${number(reward.reward_denarios)} Denários · ${number(reward.mmr_delta)} MMR</span></aside>`
    : '';
  const phaseLabel = data.status === 'finished'
    ? winnerLabel
    : prep
      ? (data.mulligan_done ? 'Aguardando adversário' : 'Preparação inicial')
      : (data.is_your_turn ? 'Sua vez' : (data.is_ai_match ? 'NARA está pensando' : 'Vez do adversário'));
  const prepPanel = prep
    ? `<div class="gwent-prep"><span>Troque até 2 cartas ou mantenha sua mão · ${number(data.draw_count || 0)} reserva(s)</span><button class="secondary" data-gwent-keep ${data.mulligan_done ? 'disabled' : ''}>Manter mão</button><button class="primary" data-gwent-mulligan ${data.mulligan_done ? 'disabled' : ''}>Trocar selecionadas</button></div>`
    : '';
  const canPlayFromHand = data.status === 'active' && !!data.is_your_turn && !prep && !mine.passed;
  const handCardCount = Math.max(1, hand.length);
  const handCardWidth = hand.length
    ? Math.max(112, Math.min(208, Math.floor((window.innerWidth - 64 - Math.max(0, hand.length - 1) * 10) / hand.length)))
    : 210;
  const handMaxWidth = Math.min(Math.max(320, window.innerWidth - 48), hand.length * handCardWidth + Math.max(0, hand.length - 1) * 10);
  const handLayoutStyle = `--hand-count:${handCardCount};--hand-max-width:${handMaxWidth}px`;
  const handMarkup = hand.map(card => {
    const cardId = escapeHTML(card.id);
    const cardName = escapeHTML(card.nome || 'Carta');
    const swapControl = prep
      ? `<input class="gwent-hand-swap-input" type="checkbox" data-gwent-swap value="${cardId}" aria-label="Marcar ${cardName} para troca" ${data.mulligan_done || !(data.draw_count > 0) ? 'disabled' : ''}>`
      : '';
    return `<article class="gwent-unit gwent-hand-card" data-gwent-hand-card="${cardId}" role="button" tabindex="0" aria-pressed="false" aria-label="Selecionar ${cardName}" title="${cardName}">
      ${cardImageMarkup(card, cardName)}
      ${swapControl}
    </article>`;
  }).join('') || '<div class="gwent-empty-hand">Sua mão está vazia.</div>';

  const factionName = data.faction || mine.faction || '—';
  const factionInfo = (gwentFactionInfo[factionName] || {}).description || 'Sinergias de facção ativas.';
  const leaderDescription = data.leader_description || factionInfo;
  const actionDisabled = !data.is_your_turn || data.status !== 'active' || prep;
  const myTurn = data.status === 'active' && !prep && !!data.is_your_turn && !mine.passed;
  const enemyTurn = data.status === 'active' && !prep && !data.is_your_turn && !theirs.passed;
  const turnClass = prep ? 'prep' : data.status === 'finished' ? 'finished' : mine.passed ? 'passed' : myTurn ? 'mine' : 'enemy';
  const turnHeadline = prep ? (data.mulligan_done ? 'PREPARAÇÃO CONCLUÍDA' : 'PREPARE SUA MÃO')
    : data.status === 'finished' ? 'PARTIDA ENCERRADA'
    : mine.passed ? 'VOCÊ JÁ PASSOU'
    : myTurn ? 'SUA VEZ DE JOGAR' : (data.is_ai_match ? 'VEZ DA NARA IA' : 'VEZ DO ADVERSÁRIO');
  const turnSubline = prep ? 'Troque até duas cartas ou mantenha sua mão.'
    : data.status === 'finished' ? 'Confira o resultado da partida.'
    : mine.passed ? 'Aguarde o adversário concluir a rodada.'
    : myTurn ? 'Escolha uma carta e jogue na fileira adequada.' : (data.is_ai_match ? 'A NARA está calculando a próxima jogada.' : 'Seus controles estão pausados até o adversário agir.');
  const turnAnnouncement = data.status === 'finished' ? 'finished' : prep ? 'prep' : mine.passed ? 'passed' : myTurn ? 'mine' : 'enemy';
  if (gwentLastTurnAnnouncement !== null && gwentLastTurnAnnouncement !== turnAnnouncement && data.status === 'active') {
    if (myTurn) window.gwentBanner?.('SUA VEZ — ESCOLHA UMA CARTA');
    else if (data.is_ai_match) window.gwentBanner?.('A NARA ESTÁ JOGANDO');
    else window.gwentBanner?.('VEZ DO ADVERSÁRIO');
  }
  gwentLastTurnAnnouncement = turnAnnouncement;

  replaceGwentArenaMarkup(arena, `<div class="gwent-arena-head">
      <div class="gwent-arena-title"><small class="eyebrow">GWENT DO COLISEU · RODADA ${number(data.round)} / 3</small><h2>Arena <span>${escapeHTML(phaseLabel)}</span></h2><p class="gwent-log">${escapeHTML(data.last_event || `${opponentName} · ${data.opponent?.faction || 'Facção não informada'}`)}</p></div>
      <div class="gwent-arena-head-actions">${eventPanel}<button type="button" class="gwent-exit" data-gwent-exit>Voltar ao lobby</button></div>
    </div>
    <div class="gwent-arena-toolbar">
      <div class="gwent-score">
        <article><small>VOCÊ</small><strong>${number(mine.score)}</strong><span>${number(mine.crowns)} coroas · ${number(mine.hand)} na mão${mine.passed ? ' · passou' : ''}</span></article>
        <article><small>${escapeHTML(opponentName)}</small><strong>${number(theirs.score)}</strong><span>${number(theirs.crowns)} coroas · ${number(theirs.hand)} na mão${theirs.passed ? ' · passou' : ''}</span></article>
      </div>
      <div class="gwent-turn-indicator ${turnClass}" role="status" aria-live="polite"><strong>${turnHeadline}</strong><small>${turnSubline}</small></div>
      <div class="gwent-faction" title="${escapeHTML(leaderDescription)}"><b>${escapeHTML(factionName)}</b><span>Líder: ${escapeHTML(data.leader_name || 'Líder')}</span></div>
      ${rewardPanel}
    </div>
    <div class="gwent-battlefield" aria-label="Campo de batalha">
      <section class="gwent-board-side gwent-board-enemy ${enemyTurn ? 'is-active' : ''} ${theirs.passed ? 'is-passed' : ''}"><h3><span>CAMPO DE ${escapeHTML(opponentName)}${data.is_ai_match ? ' · NARA IA' : ''}</span>${enemyTurn ? '<b>JOGANDO AGORA</b>' : theirs.passed ? '<b>PASSOU</b>' : ''}</h3>${board(theirs, true)}</section>
      <div class="gwent-battle-line" aria-hidden="true"><span>LINHA DE CONFRONTO</span></div>
      <section class="gwent-board-side gwent-board-mine ${myTurn ? 'is-active' : ''} ${mine.passed ? 'is-passed' : ''}"><h3><span>SEU CAMPO</span>${myTurn ? '<b>SUA VEZ</b>' : mine.passed ? '<b>PASSOU</b>' : ''}</h3>${board(mine, false)}</section>
    </div>
    <div class="gwent-actions ${prep ? 'is-prep' : ''}">
      ${prepPanel}
      <div class="gwent-action-main">
        <button class="gwent-pass-button" data-gwent-pass ${actionDisabled || mine.passed ? 'disabled' : ''}>PASSAR RODADA</button>
      </div>
      <div class="gwent-action-tools">
        <label class="gwent-leader-picker"><span>FILEIRA DO LÍDER</span><select id="gwent-leader-row" aria-label="Fileira do líder" ${actionDisabled ? 'disabled' : ''}>
          <option value="melee">Corpo a corpo</option><option value="ranged">Longa distância</option><option value="siege">Cerco</option>
        </select></label>
        <button class="gwent-leader-button" data-gwent-leader ${actionDisabled || data.leader_used ? 'disabled' : ''}>USAR LÍDER</button>
        <button class="gwent-weather-button" data-gwent-weather ${actionDisabled || data.weather_used ? 'disabled' : ''}>CLIMA</button>
        <button class="gwent-leader-button" data-gwent-relic ${actionDisabled || !mine.equipped_relic_id || mine.relic_used ? 'disabled' : ''}>ATIVAR RELÍQUIA</button>
        <button class="gwent-surrender-button" data-gwent-surrender ${data.status !== 'active' ? 'disabled' : ''}>DESISTIR</button>
      </div>
    </div>
    <section class="gwent-hand-zone ${handIsOpen ? 'is-open' : ''}">
      <div class="gwent-hand-head">
        <div class="gwent-hand-info"><h3>SUA MÃO <span>${number(hand.length)} CARTAS</span></h3><small>${data.is_your_turn && !prep && !mine.passed ? 'Escolha a fileira na carta e pressione Jogar' : prep ? 'Marque até duas cartas para trocar' : 'A mão fica protegida enquanto a NARA / adversário joga'}</small></div>
        <button type="button" class="gwent-hand-toggle ${handIsOpen ? 'is-open' : ''}" data-gwent-hand-toggle data-count="${number(hand.length)}" aria-expanded="${handIsOpen ? 'true' : 'false'}" aria-controls="gwent-hand-cards">${handIsOpen ? 'OCULTAR CARTAS' : `MOSTRAR MINHA MÃO · ${number(hand.length)}`}</button>
      </div>
      <div class="gwent-hand" id="gwent-hand-cards" data-can-play="${canPlayFromHand ? 'true' : 'false'}" style="${handLayoutStyle}" ${handIsOpen ? '' : 'hidden'}>${handMarkup}</div>
    </section>`);
  gwentSelectedHandCard = gwentHandCardsById.has(String(gwentSelectedHandCard)) ? gwentSelectedHandCard : '';
}

function showGwentResultOverlay(data, roundResult = null) {
  document.getElementById('gwent-round-result')?.remove();
  const myId = String(data.your_id || '');
  const opponentName = data.opponent?.name || 'Adversário';
  const final = data.status === 'finished';
  const finalWinner = data.winner_id == null ? null : String(data.winner_id);
  const roundOutcome = roundResult?.result || 'draw';
  // O resultado final é decidido pelo total de coroas, não pelo vencedor da última rodada.
  const outcome = final
    ? (finalWinner == null ? 'draw' : finalWinner === myId ? 'win' : 'loss')
    : roundOutcome;
  const headline = final
    ? (outcome === 'win' ? 'VOCÊ VENCEU A PARTIDA' : outcome === 'loss' ? 'VOCÊ PERDEU A PARTIDA' : 'PARTIDA EMPATADA')
    : (outcome === 'win' ? `VOCÊ VENCEU A RODADA ${number(roundResult?.round)}`
      : outcome === 'loss' ? `VOCÊ PERDEU A RODADA ${number(roundResult?.round)}` : `RODADA ${number(roundResult?.round)} EMPATADA`);
  const subline = roundResult
    ? `Você ${number(roundResult.your_score)} × ${number(roundResult.opponent_score)} ${escapeHTML(opponentName)}`
    : (data.last_event || 'Resultado final registrado.');
  const scoreLine = roundResult
    ? `<div class="gwent-result-score"><span>SUA PONTUAÇÃO</span><strong>${number(roundResult.your_score)}</strong><i>×</i><strong>${number(roundResult.opponent_score)}</strong><span>${escapeHTML(opponentName)}</span></div>`
    : `<div class="gwent-result-crowns"><span>SUAS COROAS <b>${number(data.crowns?.[myId] || 0)}</b></span><span>COROAS DO ADVERSÁRIO <b>${number(data.crowns?.[String(data.opponent?.id || '')] || 0)}</b></span></div>`;
  const reward = final && data.reward
    ? `<div class="gwent-result-rewards">Recompensas: +${number(data.reward.reward_xp)} XP · +${number(data.reward.reward_denarios)} Denários · ${number(data.reward.mmr_delta)} MMR</div>` : '';
  const overlay = document.createElement('div');
  overlay.id = 'gwent-round-result';
  overlay.className = `gwent-result-overlay ${outcome}`;
  overlay.setAttribute('role', 'dialog');
  overlay.setAttribute('aria-modal', 'true');
  overlay.setAttribute('aria-labelledby', 'gwent-result-title');
  overlay.innerHTML = `<section class="gwent-result-card"><small class="eyebrow">${final ? 'RESULTADO FINAL' : 'FIM DA RODADA'}</small><h2 id="gwent-result-title">${headline}</h2><p>${subline}</p>${scoreLine}${reward}<div class="gwent-result-actions">${final ? '<button type="button" class="primary" data-gwent-exit>VOLTAR AO LOBBY</button>' : '<button type="button" class="primary" data-gwent-result-close>CONTINUAR</button>'}</div></section>`;
  document.body.appendChild(overlay);
  overlay.querySelector('button')?.focus({preventScroll:true});
}

async function parseGwentApiResponse(response) {
  const raw = await response.text();
  try {
    return raw ? JSON.parse(raw.replace(/^\uFEFF/, '').trim()) : {};
  } catch (error) {
    const preview = raw.replace(/\s+/g, ' ').slice(0, 220);
    throw new Error(`Resposta inválida da API Gwent (HTTP ${response.status}): ${preview || 'corpo vazio'}`);
  }
}

async function refreshGwentMatch() {
  if (!currentGwentMatch || gwentActionInFlight) return true;
  // Um único GET por vez; intervalos não podem empilhar requisições lentas.
  if (gwentRefreshPromise) return gwentRefreshPromise;

  const matchId = Number(currentGwentMatch);
  const epoch = gwentRefreshEpoch;
  gwentRefreshPromise = (async () => {
    try {
      const response = await fetch(`/api/gwent/matches/${matchId}`, {credentials:'same-origin', cache:'no-store'});
      const data = await parseGwentApiResponse(response);

      // Descarta respostas antigas se a partida mudou ou houve uma jogada durante o GET.
      if (Number(currentGwentMatch) !== matchId || epoch !== gwentRefreshEpoch) return true;
      if (!response.ok) throw new Error(data.error || 'Não foi possível abrir a partida.');
      if (data.status === 'pending') {
        showNotice('Este convite ainda aguarda resposta. Consulte a lista de desafios para aceitar ou cancelar.', 'info');
        await loadGwentMatches();
        return false;
      }
      if (data.status === 'declined' || data.status === 'cancelled') {
        showNotice(data.status === 'declined' ? 'Este convite foi recusado.' : 'Este convite foi cancelado.', 'info');
        await loadGwentMatches();
        return false;
      }

      // O endpoint é consultado periodicamente, mas a arena só é redesenhada
      // quando o estado realmente muda. Isso mantém as imagens e a mão estáveis.
      const signature = JSON.stringify(data);
      if (signature !== gwentLastRenderSignature) {
        renderGwentArena(data);
        gwentLastRenderSignature = signature;
      }

      const completedRounds = Array.isArray(data.rounds) ? data.rounds : [];
      if (!gwentInitialSnapshotLoaded) {
        // Ao abrir uma partida em andamento, não reproduz resultados antigos.
        // Ao abrir uma partida finalizada pelo histórico, mostra o placar final.
        gwentInitialSnapshotLoaded = true;
        gwentSeenRoundCount = completedRounds.length;
        if (data.status === 'finished') showGwentResultOverlay(data, completedRounds.at(-1) || null);
      } else {
        const newRounds = completedRounds.slice(gwentSeenRoundCount);
        if (newRounds.length) {
          gwentSeenRoundCount = completedRounds.length;
          showGwentResultOverlay(data, newRounds[newRounds.length - 1]);
        } else if (data.status === 'finished' && !gwentPreviouslyFinished) {
          // Rendição ou encerramento administrativo não acrescenta uma rodada.
          showGwentResultOverlay(data, null);
        }
      }
      gwentPreviouslyFinished = data.status === 'finished';
      gwentMatchFinished = data.status === 'finished';
      if (gwentMatchFinished && gwentPoll) { clearInterval(gwentPoll); gwentPoll = null; }
      return true;
    } catch (error) {
      if (Number(currentGwentMatch) === matchId && epoch === gwentRefreshEpoch) {
        showNotice(error.message, 'error');
      }
      return false;
    } finally {
      gwentRefreshPromise = null;
    }
  })();
  return gwentRefreshPromise;
}

async function openGwentMatch(id) {
  document.body.classList.add('gwent-match-active');
  document.documentElement.classList.add('gwent-match-active');
  // Invalida qualquer resposta da partida anterior antes de trocar o contexto.
  gwentRefreshEpoch += 1;
  if (gwentPoll) { clearInterval(gwentPoll); gwentPoll = null; }
  if (gwentRefreshPromise) await gwentRefreshPromise;
  currentGwentMatch = Number(id);
  gwentHandOpen = null;
  gwentHandLastPhase = null;
  gwentSelectedHandCard = '';
  gwentHandCardsById = new Map();
  gwentLastTurnAnnouncement = null;
  gwentMatchFinished = false;
  gwentLastRenderSignature = '';
  gwentInitialSnapshotLoaded = false;
  gwentSeenRoundCount = 0;
  gwentPreviouslyFinished = false;
  document.getElementById('gwent-round-result')?.remove();
  const canOpen = await refreshGwentMatch();
  if (!canOpen) { currentGwentMatch = null; document.body.classList.remove('gwent-match-active'); document.documentElement.classList.remove('gwent-match-active'); return; }
  if (!gwentMatchFinished) {
    gwentPoll = setInterval(() => {
      if (!document.hidden) refreshGwentMatch();
    }, 3500);
  }
  const arena = $('#gwent-arena');
  const bounds = arena.getBoundingClientRect();
  if (!document.body.classList.contains('gwent-match-active') && (bounds.top < 0 || bounds.bottom > window.innerHeight)) {
    const root = document.documentElement;
    const oldBehavior = root.style.scrollBehavior;
    root.style.scrollBehavior = 'auto';
    arena.scrollIntoView({behavior:'auto', block:'nearest'});
    root.style.scrollBehavior = oldBehavior;
  }
}
async function respondGwentMatch(matchId, action) {
  try {
    const response = await fetch(`/api/gwent/matches/${Number(matchId)}/respond`, {
      method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({action})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Não foi possível responder ao convite.');
    await loadGwentMatches();
    if (action === 'accept') {
      showNotice('Convite aceito. A partida começou.', 'success');
      await openGwentMatch(data.match_id);
    } else {
      showNotice(action === 'decline' ? 'Convite recusado.' : 'Convite cancelado.', 'success');
    }
  } catch (error) { showNotice(error.message, 'error'); }
}
async function sendGwentAction(action, card_id = '', row = '', card_ids = [], target_id = '') {
  if (!currentGwentMatch || gwentActionInFlight) return;
  const matchId = Number(currentGwentMatch);
  gwentActionInFlight = true;
  // Invalida qualquer GET iniciado antes da jogada para ele não sobrescrever o estado novo.
  gwentRefreshEpoch += 1;
  try {
    const r = await fetch(`/api/gwent/matches/${matchId}/action`, {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'}, body:JSON.stringify({action, card_id, row, card_ids, target_id})});
    const data = await parseGwentApiResponse(r); if (!r.ok) throw new Error(data.error || 'Jogada recusada.');
    if (gwentRefreshPromise) await gwentRefreshPromise;
    if (Number(currentGwentMatch) === matchId) {
      gwentActionInFlight = false;
      await refreshGwentMatch();
    }
  } catch(e) {
    showNotice(e.message, 'error');
  } finally {
    gwentActionInFlight = false;
  }
}

$('#atelier-card').addEventListener('change', () => {
  atelierPromptText = ''; atelierNegativeText = ''; atelierAnalysisText = ''; $('#atelier-analysis').value = ''; $('#atelier-prompt').value = ''; $('#atelier-negative').value = ''; $('#atelier-copy-prompt').disabled = true; $('#atelier-copy-negative').disabled = true; $('#atelier-copy-bundle').disabled = true;
  loadAtelierOfficialArt();
});
$('#atelier-generate-prompt').addEventListener('click', generateAtelierPrompt);
$('#atelier-copy-prompt').addEventListener('click', async () => {
  if (!atelierPromptText) return;
  try { await navigator.clipboard.writeText(atelierPromptText); showNotice('Prompt copiado.', 'success'); }
  catch { $('#atelier-prompt').focus(); $('#atelier-prompt').select(); showNotice('Selecione e copie o prompt manualmente.', 'info'); }
});
$('#atelier-copy-negative').addEventListener('click', async () => {
  if (!atelierNegativeText) return;
  try { await navigator.clipboard.writeText(atelierNegativeText); showNotice('Negative prompt copiado.', 'success'); }
  catch { $('#atelier-negative').focus(); $('#atelier-negative').select(); showNotice('Selecione e copie o negative prompt manualmente.', 'info'); }
});
$('#atelier-copy-bundle').addEventListener('click', async () => {
  if (!atelierPromptText || !atelierNegativeText || !atelierAnalysisText) return;
  const bundle = `A. ANÁLISE ARTÍSTICA\n${atelierAnalysisText}\n\nB. PROMPT PROFISSIONAL\n${atelierPromptText}\n\nC. NEGATIVE PROMPT\n${atelierNegativeText}`;
  try { await navigator.clipboard.writeText(bundle); showNotice('Pacote A+B+C copiado.', 'success'); }
  catch { showNotice('A cópia automática falhou. Copie os três campos manualmente.', 'info'); }
});
$('#atelier-image').addEventListener('change', () => {
  const file = $('#atelier-image').files?.[0];
  const preview = $('#atelier-preview');
  if (atelierPreviewUrl) URL.revokeObjectURL(atelierPreviewUrl);
  atelierPreviewUrl = '';
  if (!file) { preview.hidden = true; $('#atelier-submit').disabled = true; return; }
  if (!['image/png','image/jpeg','image/webp'].includes(file.type) || file.size > 8 * 1024 * 1024) {
    showNotice('Formato inválido ou arquivo acima de 8 MB.', 'error'); preview.hidden = true; $('#atelier-submit').disabled = true; return;
  }
  atelierPreviewUrl = URL.createObjectURL(file); preview.src = atelierPreviewUrl; preview.hidden = false; $('#atelier-submit').disabled = false;
});
$('#atelier-submit').addEventListener('click', submitAtelierArt);
document.addEventListener('click', event => {
  const approve = event.target.closest('[data-atelier-approve]');
  const reject = event.target.closest('[data-atelier-reject]');
  if (approve) decideAtelierSubmission(Number(approve.dataset.atelierApprove), true);
  if (reject) decideAtelierSubmission(Number(reject.dataset.atelierReject), false);
});

$('#gwent-faction').addEventListener('change', () => { renderGwentLeaderOptions(); renderGwentBuilder(); });
$('#gwent-leader').addEventListener('change', () => { renderGwentLeaderOptions($('#gwent-leader').value); renderGwentBuilder(); });
$('#gwent-card-search').addEventListener('input', renderGwentBuilder);
$('#gwent-filter-faction').addEventListener('change', renderGwentBuilder);
$('#gwent-filter-rarity').addEventListener('change', renderGwentBuilder);
$('#gwent-save-deck').addEventListener('click', saveGwentDeck);
$('#gwent-reset-deck').addEventListener('click', resetGwentDeck);
$('#atelier-remove-all-art')?.addEventListener('click', removeAllAtelierArts);
$('#atelier-leader-art-select')?.addEventListener('change', updateAtelierLeaderArtPreview);
$('#atelier-leader-art-file')?.addEventListener('change', () => {
  const file = $('#atelier-leader-art-file')?.files?.[0];
  const status = $('#atelier-leader-art-status');
  if (file && status) status.textContent = `${file.name} selecionado · ${Math.max(1, Math.round(file.size / 1024))} KB. A imagem será normalizada para 1200 × 960 px (5:4).`;
});
$('#atelier-leader-art-upload')?.addEventListener('click', uploadAtelierLeaderArt);
$('#atelier-leader-art-remove')?.addEventListener('click', removeAtelierLeaderArt);
$('#gwent-create-match').addEventListener('click', createGwentMatch);
$('#gwent-solo-match')?.addEventListener('click', createGwentSoloMatch);
$('#gwent-open-pack').addEventListener('click', buyGwentPack);

function closeGwentHandHoverPreview() {
  document.getElementById('gwent-hand-hover-preview')?.remove();
}
function showGwentImageHoverPreview(source, alt = '') {
  if (!source) return closeGwentHandHoverPreview();
  closeGwentHandHoverPreview();
  const preview = document.createElement('div');
  preview.id = 'gwent-hand-hover-preview';
  preview.setAttribute('aria-hidden', 'true');
  const image = document.createElement('img');
  image.alt = alt || '';
  try {
    const highRes = new URL(source, window.location.origin);
    if (highRes.pathname.includes('/api/gwent/cards/')) {
      highRes.searchParams.delete('thumb');
      highRes.searchParams.set('detail', '1');
    }
    image.src = `${highRes.pathname}${highRes.search}`;
  } catch {
    image.src = source;
  }
  preview.appendChild(image);
  document.body.appendChild(preview);
}
function showGwentHandHoverPreview(cardId) {
  const card = gwentHandCardsById.get(String(cardId || ''));
  if (!card) return closeGwentHandHoverPreview();
  showGwentImageHoverPreview(imageUrl(card), card.nome || 'Carta');
}

function closeGwentBoardCardModal() {
  document.getElementById('gwent-board-card-modal')?.remove();
}

function openGwentBoardCardModal(cardId) {
  const card = gwentBoardCardsById.get(String(cardId || ''));
  if (!card) return;
  closeGwentHandHoverPreview();
  closeGwentBoardCardModal();
  closeGwentPlayCardModal();

  const modal = document.createElement('div');
  modal.id = 'gwent-board-card-modal';
  modal.className = 'gwent-board-card-modal';
  modal.setAttribute('role', 'dialog');
  modal.setAttribute('aria-modal', 'true');
  modal.setAttribute('aria-label', `Inspeção de combate: ${card.nome || 'carta'}`);

  const basePower = Number(card.poder || 0);
  const bonus = Number(card.bonus || 0);
  const currentPower = Math.max(1, basePower + bonus);
  const shield = Number(card.escudo || 0);
  const rarityBudget = rarityPower(card);
  const rowLabel = card.row_label || gwentRowLabel(card.row || '');
  const isSpecial = !!card.especial || card.categoria === 'Especial';
  const modalCard = {...card};
  const src = imageUrl(card);
  if (src.includes('/api/gwent/cards/')) {
    const hi = new URL(src, window.location.origin);
    hi.searchParams.delete('thumb');
    hi.searchParams.set('detail', '1');
    modalCard.image_url = `${hi.pathname}${hi.search}`;
  }

  modal.innerHTML = `
    <section class="gwent-board-card-dialog">
      <button type="button" class="gwent-board-card-close" data-gwent-board-close aria-label="Fechar">×</button>
      <div class="gwent-board-card-art">${cardImageMarkup(modalCard, card.nome || 'Carta')}</div>
      <div class="gwent-board-card-info">
        <small class="gwent-board-card-eyebrow">GWENT DO COLISEU · INSPEÇÃO DE COMBATE</small>
        <h2>${escapeHTML(card.nome || 'Carta')}</h2>
        <div class="gwent-board-card-tags v51-inspection-tags">
          <span><i>${cardSigil(card.faccao || card.tipo || 'Especial')}</i>${escapeHTML(card.faccao || card.tipo || 'Coliseu')}</span>
          <span><i>${cardSigil(card.raridade || 'Carta')}</i>${escapeHTML(card.raridade || 'Carta')}</span>
          <span><i>${cardSigil(isSpecial ? 'Especial' : rowLabel)}</i>${escapeHTML(isSpecial ? 'Carta especial' : rowLabel)}</span>
          <span>EM CAMPO</span>
        </div>
        <div class="gwent-board-card-stats">
          <article><small>PODER ATUAL</small><strong>${number(currentPower)}</strong></article>
          <article><small>BÔNUS</small><strong>${bonus > 0 ? '+' : ''}${number(bonus)}</strong></article>
          <article><small>ESCUDO</small><strong>${number(shield)}</strong></article>
          <article class="gwent-rarity-potency"><small>POTÊNCIA DA RARIDADE</small><strong>${number(rarityBudget)} / 6</strong></article>
        </div>
        <section class="gwent-board-card-ability">
          <small>HABILIDADE</small>
          <strong>${escapeHTML(card.habilidade_nome || 'Sem habilidade especial')}</strong>
          <p>${escapeHTML(card.habilidade_texto || 'Sem habilidade especial.')}</p>
        </section>
        ${card.descricao ? `<section class="gwent-board-card-ability gwent-board-card-lore"><small>DESCRIÇÃO</small><p>${escapeHTML(card.descricao)}</p></section>` : ''}
        <p class="gwent-board-card-note"><strong>Como ler o poder:</strong> o número impresso na carta é o poder-base (${number(basePower)}). O bônus de combate é ${bonus > 0 ? "+" : ""}${number(bonus)}. Por isso, o poder atual é ${number(currentPower)} (poder-base + bônus, com mínimo de 1). A potência da raridade melhora apenas os efeitos da habilidade; ela não é somada ao poder.</p>
        <button type="button" class="gwent-board-card-dismiss" data-gwent-board-close>FECHAR INSPEÇÃO</button>
      </div>
    </section>`;
  document.body.appendChild(modal);
  observeCardImages(modal);
  modal.addEventListener('click', event => {
    if (event.target === modal || event.target.closest('[data-gwent-board-close]')) {
      closeGwentBoardCardModal();
    }
  });
  modal.querySelector('[data-gwent-board-close]')?.focus();
}

function closeGwentPlayCardModal() {
  document.getElementById('gwent-play-card-modal')?.remove();
}
function openGwentPlayCardModal(cardId) {
  const card = gwentHandCardsById.get(String(cardId || ''));
  if (!card) return;
  closeGwentHandHoverPreview();
  closeGwentPlayCardModal();
  const arena = document.getElementById('gwent-arena');
  const hand = arena?.querySelector('#gwent-hand-cards');
  const canPlay = hand?.dataset.canPlay === 'true';
  const prep = !!arena?.querySelector('.gwent-prep');
  const modal = document.createElement('div');
  modal.id = 'gwent-play-card-modal';
  modal.className = 'gwent-play-card-modal';
  modal.dataset.cardId = String(card.id);
  modal.setAttribute('role', 'dialog');
  modal.setAttribute('aria-modal', 'true');
  modal.setAttribute('aria-label', `Preparar jogada: ${card.nome || 'carta'}`);
  const isSpecial = !!(card.especial || String(card.categoria || '').toLowerCase() === 'especial');
  const row = ['melee','ranged','siege'].includes(card.row || card.fileira) ? (card.row || card.fileira) : 'melee';
  const rowNames = {melee:'Corpo a corpo',ranged:'Longa distância',siege:'Cerco'};
  const rowTargetSkills = new Set(['gwent_nevoa','gwent_chifre','gwent_execucao','gwent_vinculo','gwent_muralha','gwent_sangramento','gwent_geada_cariana','gwent_podrida','gwent_loucura','gwent_invocacao','gwent_passo']);
  const needsRowChoice = isSpecial && rowTargetSkills.has(String(card.habilidade || ''));
  const options = (isSpecial && needsRowChoice ? [['melee','Corpo a corpo'],['ranged','Longa distância'],['siege','Cerco']] : [[row,rowNames[row]]])
    .map(([v,l]) => `<option value="${v}" ${row === v ? 'selected' : ''}>${l}</option>`).join('');
  const power = isSpecial ? 'Carta especial · efeito tático' : `${number(card.poder)} poder`;
  const stateText = prep ? 'Na preparação, marque a carta para incluí-la na troca.'
    : canPlay && !isSpecial ? `Esta unidade só pode entrar em ${rowNames[row]}.`
    : canPlay && needsRowChoice ? 'Escolha a fileira afetada pelo efeito.'
    : canPlay ? 'Esta tática não exige escolha de fileira.'
    : 'Você poderá jogar esta carta quando chegar sua vez.';
  const modalCard = {...card};
  const modalImageUrl = imageUrl(card);
  if (modalImageUrl.includes('/api/gwent/cards/')) {
    const highRes = new URL(modalImageUrl, window.location.origin);
    highRes.searchParams.delete('thumb');
    highRes.searchParams.set('detail', '1');
    modalCard.image_url = `${highRes.pathname}${highRes.search}`;
  }
  modal.innerHTML = `
    <section class="gwent-play-card-dialog">
      <button type="button" class="gwent-play-card-close" data-gwent-modal-close aria-label="Fechar">×</button>
      <div class="gwent-play-card-art">${cardImageMarkup(modalCard, card.nome || 'Carta')}</div>
      <div class="gwent-play-card-info">
        <small class="eyebrow">PREPARAR JOGADA</small>
        <h2>${escapeHTML(card.nome || 'Carta')}</h2>
        <div class="gwent-play-card-tags"><span>${escapeHTML(card.raridade || 'Carta')}</span><span>${escapeHTML(power)}</span></div>
        <section class="gwent-play-card-ability">
          <small>HABILIDADE</small>
          <strong>${escapeHTML(card.habilidade_nome || 'Sem habilidade especial')}</strong>
          <p>${escapeHTML(card.habilidade_texto || 'Sem habilidade especial.')}</p>
        </section>
        ${card.descricao ? `<section class="gwent-play-card-ability gwent-play-card-lore"><small>DESCRIÇÃO</small><p>${escapeHTML(card.descricao)}</p></section>` : ''}
        <p class="gwent-play-card-state">${escapeHTML(stateText)}</p>
        <label class="gwent-play-card-row" style="${(!isSpecial || !needsRowChoice) ? 'display:none' : ''}"><span>FILEIRA DO EFEITO</span>
          <select data-gwent-modal-row ${canPlay && !prep && needsRowChoice ? '' : 'disabled'}>${options}</select>
        </label>
        <button type="button" class="gwent-play-card-confirm" data-gwent-modal-play ${canPlay && !prep ? '' : 'disabled'}>JOGAR CARTA</button>
      </div>
    </section>`;
  document.body.appendChild(modal);
  observeCardImages(modal);
  modal.addEventListener('click', event => {
    if (event.target === modal || event.target.closest('[data-gwent-modal-close]')) {
      closeGwentPlayCardModal(); return;
    }
    const play = event.target.closest('[data-gwent-modal-play]');
    if (!play || play.disabled) return;
    const selectedRow = modal.querySelector('[data-gwent-modal-row]')?.value || row;
    closeGwentPlayCardModal();
    const targetInfo = gwentOpcoesDoAlvo(String(card.id), selectedRow);
    if (targetInfo && targetInfo.opcoes.length) openGwentTargetPicker(String(card.id), selectedRow, targetInfo);
    else sendGwentAction('play', String(card.id), selectedRow);
  });
  modal.querySelector('[data-gwent-modal-close]')?.focus();
}
document.addEventListener('mouseover', event => {
  const handCard = event.target.closest('[data-gwent-hand-card]');
  if (handCard && !handCard.contains(event.relatedTarget)) {
    showGwentHandHoverPreview(handCard.dataset.gwentHandCard);
    return;
  }
  const boardCard = event.target.closest('.gwent-board-card');
  if (boardCard && !boardCard.contains(event.relatedTarget)) {
    const image = boardCard.querySelector('img[data-card-src]');
    if (image) showGwentImageHoverPreview(image.dataset.cardSrc || image.currentSrc || image.src, image.alt);
  }
});
document.addEventListener('mouseout', event => {
  const handCard = event.target.closest('[data-gwent-hand-card]');
  if (handCard && !handCard.contains(event.relatedTarget)) {
    closeGwentHandHoverPreview();
    return;
  }
  const boardCard = event.target.closest('.gwent-board-card');
  if (boardCard && !boardCard.contains(event.relatedTarget)) closeGwentHandHoverPreview();
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape') { closeGwentPlayCardModal(); closeGwentBoardCardModal(); closeGwentHandHoverPreview(); }
});

document.addEventListener('keydown', event => {
  const boardCard = event.target.closest('.gwent-board-card[data-card-id]');
  if (!boardCard || (event.key !== 'Enter' && event.key !== ' ')) return;
  event.preventDefault();
  openGwentBoardCardModal(boardCard.dataset.cardId);
});

document.addEventListener('keydown', event => {
  const handCard = event.target.closest('[data-gwent-hand-card]');
  if (!handCard || (event.key !== 'Enter' && event.key !== ' ')) return;
  event.preventDefault();
  handCard.click();
});

document.addEventListener('click', async event => {
  const boardCard = event.target.closest('.gwent-board-card[data-card-id]');
  if (boardCard) {
    openGwentBoardCardModal(boardCard.dataset.cardId);
    return;
  }
  const handCard = event.target.closest('[data-gwent-hand-card]');
  if (handCard) {
    const cardId = String(handCard.dataset.gwentHandCard || '');
    if (document.querySelector('#gwent-arena .gwent-prep')) {
      const swap = handCard.querySelector('[data-gwent-swap]');
      if (swap && !swap.disabled && event.target !== swap) swap.checked = !swap.checked;
      handCard.classList.toggle('is-swap-marked', !!swap?.checked);
    } else {
      gwentSelectedHandCard = cardId;
      openGwentPlayCardModal(cardId);
    }
    return;
  }
  const selectHandCard = event.target.closest('[data-gwent-select-card]');
  if (selectHandCard) {
    updateGwentSelectedCardUI(selectHandCard.dataset.gwentSelectCard);
    return;
  }
  const playSelected = event.target.closest('[data-gwent-play-selected]');
  if (playSelected) {
    const cardId = String(gwentSelectedHandCard || '');
    const rowSelect = $('#gwent-selected-row');
    const row = rowSelect ? rowSelect.value : (gwentHandCardsById.get(cardId)?.row || 'melee');
    if (!cardId || playSelected.disabled) return;
    const info = gwentOpcoesDoAlvo(cardId, row);
    if (info && info.opcoes.length) openGwentTargetPicker(cardId, row, info);
    else sendGwentAction('play', cardId, row);
    return;
  }
  const add = event.target.closest('[data-gwent-add]'); const remove = event.target.closest('[data-gwent-remove]');
  const play = event.target.closest('[data-gwent-play]'); const open = event.target.closest('[data-gwent-open]');
  const respond = event.target.closest('[data-gwent-respond]');
  const closeRoundResult = event.target.closest('[data-gwent-result-close]');
  if (closeRoundResult) {
    document.getElementById('gwent-round-result')?.remove();
    return;
  }
  const handToggle = event.target.closest('[data-gwent-hand-toggle]');
  if (handToggle) {
    const zone = handToggle.closest('.gwent-hand-zone');
    const nextOpen = !zone?.classList.contains('is-open');
    gwentHandOpen = nextOpen;
    // O estado da mão também controla a distribuição vertical da arena:
    // recolhida libera altura para o campo; aberta restaura a área da mão.
    document.getElementById('gwent-arena')?.classList.toggle('hand-open', nextOpen);
    zone?.classList.toggle('is-open', nextOpen);
    zone?.querySelector('.gwent-hand')?.toggleAttribute('hidden', !nextOpen);
    handToggle.classList.toggle('is-open', nextOpen);
    handToggle.setAttribute('aria-expanded', String(nextOpen));
    handToggle.textContent = nextOpen ? 'OCULTAR CARTAS' : `MOSTRAR MINHA MÃO · ${handToggle.dataset.count || '0'}`;
    return;
  }
  const exitArena = event.target.closest('[data-gwent-exit]');
  if (exitArena) {
    document.getElementById('gwent-round-result')?.remove();
    document.body.classList.remove('gwent-match-active');
    document.documentElement.classList.remove('gwent-match-active');
    currentGwentMatch = null;
    gwentHandOpen = null;
    gwentHandLastPhase = null;
    gwentSelectedHandCard = '';
    gwentHandCardsById = new Map();
    gwentLastTurnAnnouncement = null;
    gwentRefreshEpoch += 1;
    if (gwentPoll) { clearInterval(gwentPoll); gwentPoll = null; }
    $('#gwent-arena').hidden = true;
    await loadGwentMatches();
    return;
  }
  const evolve = event.target.closest('[data-gwent-evolve]');
  if (evolve) {
    evolve.disabled = true;
    try {
      const response = await fetch('/api/gwent/evolve', {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'}, body:JSON.stringify({exemplar_id:Number(evolve.dataset.gwentEvolve)})});
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || (result.status === 'fragmentos_insuficientes' ? `Você precisa de ${result.necessarios} fragmentos; possui ${result.saldo}.` : result.status === 'destino_ja_possuido' ? `Você já possui um exemplar ${result.rarity} deste modelo. Lapide esse exemplar ou escolha outra evolução.` : 'Não foi possível evoluir esta carta.'));
      showNotice(`Ascensão concluída: ${result.rarity} · ${result.power}/${result.max_power ?? result.power} poder. O potencial de lapidação foi ampliado.`, 'success');
      await loadAccount(); await loadGwentDeck(); await loadDropHistory();
    } catch (error) { showNotice(error.message, 'error'); evolve.disabled = false; }
  }
  const upgrade = event.target.closest('[data-gwent-upgrade]');
  if (upgrade) {
    upgrade.disabled = true;
    try {
      const response = await fetch('/api/gwent/upgrade', {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'}, body:JSON.stringify({exemplar_id:Number(upgrade.dataset.gwentUpgrade)})});
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || (result.status === 'almas_insuficientes' ? `Você precisa de ${result.necessarias} Almas; possui ${result.saldo}.` : 'Não foi possível lapidar esta carta.'));
      showNotice(`Carta lapidada: ${result.power}/${result.max_power} poder.`, 'success');
      await loadAccount(); await loadGwentDeck(); await loadDropHistory();
    } catch (error) { showNotice(error.message, 'error'); upgrade.disabled = false; }
  }
  if (add && gwentDeckIds.length < 12) {
    const card = collection.find(c => c.id === add.dataset.gwentAdd);
    const selected = gwentDeckIds.map(id => collection.find(c => c.id === id)).filter(Boolean);
    if (selected.some(item => (item.card_id || item.id) === (card?.card_id || card?.id))) return showNotice('O deck não pode repetir o mesmo modelo, mesmo usando exemplares diferentes.', 'error');
    const specials = selected.filter(c => c.categoria === 'Especial').length;
    if (card?.categoria === 'Especial' && specials >= 4) return showNotice('O deck aceita no máximo quatro cartas especiais.', 'error');
    gwentDeckIds.push(add.dataset.gwentAdd); renderGwentBuilder();
  }
  if (remove) { gwentDeckIds = gwentDeckIds.filter(id => id !== remove.dataset.gwentRemove); renderGwentBuilder(); }
  if (play) {
    const cardId = play.dataset.gwentPlay;
    const row = document.querySelector(`[data-gwent-row="${CSS.escape(cardId)}"]`)?.value || '';
    const info = gwentOpcoesDoAlvo(cardId, row);
    if (info && info.opcoes.length) openGwentTargetPicker(cardId, row, info); else sendGwentAction('play', cardId, row);
  }
  if (open) openGwentMatch(open.dataset.gwentOpen);
  if (respond) respondGwentMatch(respond.dataset.matchId, respond.dataset.gwentRespond);
  if (event.target.closest('[data-gwent-mulligan]')) {
    const card_ids = [...document.querySelectorAll('[data-gwent-swap]:checked')].map(x => x.value);
    sendGwentAction('mulligan', '', '', card_ids);
  }
  if (event.target.closest('[data-gwent-keep]')) sendGwentAction('keep');
  if (event.target.closest('[data-gwent-pass]')) sendGwentAction('pass');
  if (event.target.closest('[data-gwent-leader]')) sendGwentAction('leader', '', $('#gwent-leader-row').value);
  if (event.target.closest('[data-gwent-weather]')) sendGwentAction('weather', '', $('#gwent-leader-row').value);
  if (event.target.closest('[data-gwent-relic]')) openGwentRelicPicker();
  if (event.target.closest('[data-gwent-surrender]')) {
    if (window.confirm('Tem certeza de que deseja desistir? A vitória será concedida ao adversário.')) sendGwentAction('surrender');
  }
});

function showGwentPage() {
  document.querySelectorAll('.page').forEach(el => el.classList.toggle('show', el.id === 'gwent'));
}
async function loadGwentPlayers() {
  if (!currentUser) return;
  try {
    await fetch('/api/presence/heartbeat', {method:'POST', credentials:'same-origin'});
    const response = await fetch('/api/players', {credentials:'same-origin', cache:'no-store'});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Não foi possível carregar jogadores.');
    const players = (data.players || []).filter(player => !player.is_self);
    $('#gwent-opponent').innerHTML = '<option value="">Selecione um adversário</option>' + players.map(player => {
      const status = player.web_online ? ' · online no site' : ` · Discord: ${player.discord_presence}`;
      return `<option value="${escapeHTML(player.id)}">${escapeHTML(player.name)}${escapeHTML(status)}</option>`;
    }).join('');
  } catch (error) {
    const select = $('#gwent-opponent');
    if (select) select.innerHTML = `<option value="">${escapeHTML(error.message || 'Não foi possível carregar jogadores.')}</option>`;
    console.error('Falha ao carregar jogadores do Gwent:', error);
    showNotice(error.message, 'error');
  }
}

loadAccount().then(async () => {
  showGwentPage();
  if (!currentUser) return;
  await Promise.all([loadGwentDeck(), loadGwentMatches(), loadGwentPlayers(), loadDropHistory(), loadAtelier(), loadGwentStore()]);
  window.setInterval(loadGwentPlayers, 30000);
  gwentListPoll = window.setInterval(loadGwentMatches, 12000);
  const requested = new URLSearchParams(window.location.search).get('gwent');
  if (requested && /^\d+$/.test(requested)) openGwentMatch(requested);
});

/* Abertura de pacote: cartas viradas que se revelam uma a uma (clique para pular) */
function revealPack() {
  const box = document.querySelector('#gwent-pack-results .gwent-pack-opened');
  if (!box) return;
  const items = [...box.querySelectorAll('article.pk')];
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  items.forEach(el => el.classList.add('pk-hide'));
  const order = items.map((el, i) => i).sort((x, y) => (RARANK[items[x].dataset.r] || 0) - (RARANK[items[y].dataset.r] || 0));
  let timers = [];
  const show = el => { el.classList.remove('pk-hide'); el.classList.add('pk-show'); };
  order.forEach((idx, n) => timers.push(setTimeout(() => show(items[idx]), 500 + n * 750)));
  box.addEventListener('click', () => { timers.forEach(clearTimeout); items.forEach(show); }, { once: true });
  const h = box.querySelector('h4'); if (h) h.insertAdjacentHTML('afterend', '<small class="pk-skip">Clique para revelar tudo</small>');
}
const RARANK = { comum: 0, rara: 1, epica: 2, lendaria: 3, mitica: 4, primordial: 5, singular: 6 };

// --- Hub: início, comunidade e Nara (dados locais, sem custo de IA). ---
const hubFmt = (iso) => { const d = new Date(String(iso).replace(' ', 'T') + (String(iso).includes('Z') || String(iso).includes('+') ? '' : 'Z')); if (isNaN(d)) return ''; const m = Math.max(0, (Date.now() - d) / 60000); return m < 60 ? `${Math.floor(m) || 1} min` : m < 1440 ? `${Math.floor(m / 60)} h` : `${Math.floor(m / 1440)} d`; };
const hubAvatar = (url, name) => url ? `<img class="hub-av" src="${escapeHTML(url)}" alt="" loading="lazy">` : `<span class="hub-av">${escapeHTML((name || '?')[0].toUpperCase())}</span>`;
const hubName = (r) => `<span class="rank-name"${/^#[0-9a-f]{6}$/i.test(r.cor || '') ? ` style="color:${r.cor}"` : ''}>${r.emblema ? escapeHTML(r.emblema) + ' ' : ''}${escapeHTML(r.name)}</span>`;
const hubRows = (rows, unit) => rows.length ? rows.map(r => `<div class="rank-row${r.pos <= 3 ? ' top' + r.pos : ''}"><b class="rank-pos">${r.pos <= 3 ? ['🥇','🥈','🥉'][r.pos - 1] : r.pos}</b>${hubAvatar(r.avatar, r.name)}${hubName(r)}<strong>${number(r.valor)} <small>${unit}</small></strong></div>`).join('') : '<p class="muted">Ainda sem dados.</p>';
async function loadHub() {
  try {
    const r = await fetch('/api/hub/overview', {credentials: 'same-origin', cache: 'no-store'});
    if (!r.ok) return;
    const d = await r.json(), s = d.server;
    $('#hub-server').textContent = s.name;
    $('#hub-members').textContent = number(s.members); $('#hub-online').textContent = number(s.online); $('#hub-onsite').textContent = number(s.on_site);
    const icon = $('#hub-icon'); if (s.icon) { icon.src = s.icon; icon.hidden = false; }
    const inv = $('#hub-invite'); if (s.invite) { inv.href = s.invite; inv.hidden = false; }
    if (!d.authenticated) return;
    const m = d.me;
    $('#profile-name').dataset.n = m.name || 'Conta Discord'; $('#profile-status').dataset.s = m.patente; $('#profile-name').textContent = m.name || 'Conta Discord'; $('#profile-status').textContent = m.patente;
    if (m.avatar) $('.profile .avatar').innerHTML = `<img src="${escapeHTML(m.avatar)}" alt="" style="width:100%;height:100%;border-radius:50%">`;
    $('#hub-me-name').textContent = m.name || 'Você'; $('#hub-me-rank').textContent = `#${number(m.posicao)} no ranking`;
    if (m.prefs) { visSet(m.prefs, false); window.visServer = m.prefs; }
    const pf = m.prefs || {};
    const pct = Math.min(100, Math.round(m.xp_nivel_atual / Math.max(1, m.xp_nivel_total) * 100));
    $('#hub-me-body').innerHTML = `<div class="me-banner"><span class="me-emb">${escapeHTML(pf.emblema || '⚔')}</span><b>${escapeHTML(m.patente)}</b></div>${pf.frase ? `<p class="me-quote">“${escapeHTML(pf.frase)}”</p>` : ''}<div class="me-level"><b>Nível ${m.nivel}</b><span>${escapeHTML(m.patente)}</span></div><div class="xpbar" title="${pct}%"><i style="width:${pct}%"></i></div><small class="muted">${number(m.xp_nivel_atual)} / ${number(m.xp_nivel_total)} XP para o próximo nível</small><div class="me-stats"><div><b>${number(m.platinas)}</b><small>Platinas</small></div><div><b>${number(m.zerados)}</b><small>Zerados</small></div><div><b>${number(m.runs)}</b><small>Runs</small></div><div><b>${number(m.denarios)}</b><small>Denários</small></div></div>${m.pendentes ? `<p class="muted">⏳ ${m.pendentes} envio(s) aguardando aprovação.</p>` : ''}`;
    $('#hub-tops').innerHTML = [['xp','Mais XP','XP'],['platinas','Platinas','plat.'],['zerados','Zerados','jogos']].map(([k, t, u]) => `<section class="hub-card"><h4>${t}</h4>${hubRows(d.top[k], u)}</section>`).join('');
    $('#hub-recent').innerHTML = d.recent.length ? d.recent.map(a => `<div class="recent-item"><i>${a.tipo === 'platina' ? '💎' : '🏆'}</i><div><b>${escapeHTML(a.user)}</b> ${a.tipo === 'platina' ? 'platinou' : 'zerou'} <b>${escapeHTML(a.game)}</b></div><small>${hubFmt(a.quando)}</small></div>`).join('') : '<p class="muted">Nenhuma conquista recente.</p>';
  } catch (e) { /* hub é complementar: falha silenciosa */ }
}
let hubRank = 'xp';
async function loadRank(tipo = hubRank) {
  hubRank = tipo;
  document.querySelectorAll('#rank-seg button').forEach(b => b.classList.toggle('on', b.dataset.rank === tipo));
  try {
    const r = await fetch(`/api/hub/ranking?tipo=${tipo}&limite=25`, {credentials: 'same-origin', cache: 'no-store'});
    if (!r.ok) return;
    const d = await r.json(), u = d.label.toLowerCase(), t = d.rows.slice(0, 3);
    $('#rank-podium').innerHTML = t.length === 3 ? `<div class="podium">${[1, 0, 2].map(i => `<div class="pod p${i + 1}">${hubAvatar(t[i].avatar, t[i].name)}<b>${hubName(t[i])}</b><small>${number(t[i].valor)} ${u}</small><div class="pod-step">${i + 1}</div></div>`).join('')}</div>` : '';
    $('#rank-list').innerHTML = hubRows(t.length === 3 ? d.rows.slice(3) : d.rows, u);
  } catch (e) {}
}
async function loadCommunityPlayers() {
  try {
    const r = await fetch('/api/players', {credentials: 'same-origin', cache: 'no-store'});
    if (!r.ok) return;
    const d = await r.json(), q = ($('#players-search').value || '').toLowerCase();
    const st = {online: 'Online', idle: 'Ausente', dnd: 'Ocupado', offline: 'Offline'};
    $('#players-list').innerHTML = d.players.filter(p => p.name.toLowerCase().includes(q)).slice(0, 60).map(p => `<div class="player-chip">${hubAvatar(p.avatar, p.name)}<i class="dot ${p.web_online ? 'on' : p.discord_presence}"></i><span>${escapeHTML(p.name)}</span><small>${p.web_online ? 'no site' : st[p.discord_presence] || ''}</small></div>`).join('') || '<p class="muted">Ninguém encontrado.</p>';
  } catch (e) {}
}
function naraSay(txt, who) { const log = $('#nara-log'), p = document.createElement('p'); p.className = `nara-msg ${who}`; p.textContent = txt; log.appendChild(p); log.scrollTop = log.scrollHeight; return p; }
async function naraAsk(q) {
  if (!currentUser) { naraSay('Entre com Discord para falar comigo.', 'bot'); return; }
  naraSay(q, 'me'); const wait = naraSay('…', 'bot');
  try {
    const r = await fetch('/api/hub/nara', {method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({message: q})});
    const d = await r.json(); wait.textContent = d.reply || d.error || 'Algo deu errado.';
    (d.suggestions || []).forEach(s => { const b = document.createElement('button'); b.type = 'button'; b.className = 'nara-sug'; b.textContent = s; b.onclick = () => naraAsk(s); $('#nara-log').appendChild(b); });
  } catch (e) { wait.textContent = 'Sem conexão com o servidor.'; }
}
$('#nara-form')?.addEventListener('submit', (e) => { e.preventDefault(); const i = $('#nara-input'), q = i.value.trim(); if (q) { i.value = ''; naraAsk(q); } });
$('#rank-seg')?.addEventListener('click', (e) => { const b = e.target.closest('[data-rank]'); if (b) loadRank(b.dataset.rank); });
$('#players-search')?.addEventListener('input', loadCommunityPlayers);
document.addEventListener('click', (e) => { if (e.target.closest('[data-tab="community"],[data-goto="community"]')) { loadRank(); loadCommunityPlayers(); } });
loadHub(); setTimeout(() => { if (currentUser) { loadRank(); loadCommunityPlayers(); } }, 1200);
setInterval(() => { if (!document.hidden && $('#tab-home')?.classList.contains('show')) loadHub(); }, 60000);

// --- Personalização visual: tema + cor + emblema + frase (salvos no perfil). ---
const VIS_TEMAS = [['cinzas', 'Cinzas', '#9b78c4'], ['fogueira', 'Fogueira', '#ff9a3c'], ['abismo', 'Abismo', '#5fd0d6'], ['veneno', 'Veneno', '#9be564'], ['sangue', 'Sangue', '#e0525c'], ['ametista', 'Ametista', '#d9a8ff']];
const VIS_EMB = ['⚔', '🛡', '🔥', '💀', '🐉', '🌙', '👑', '🗡', '🏹', '☠', '🦅', '⚜'];
let vis = {tema: 'cinzas', cor: '', frase: '', emblema: '⚔'};
try { vis = Object.assign(vis, JSON.parse(localStorage.getItem('vis') || '{}')); } catch (e) {}
function visSet(v, save = true) {
  vis = Object.assign(vis, v); const h = document.documentElement;
  h.dataset.theme = vis.tema || 'cinzas';
  if (/^#[0-9a-f]{6}$/i.test(vis.cor || '')) { h.style.setProperty('--gold', vis.cor); h.style.setProperty('--gold-bright', `color-mix(in srgb, ${vis.cor} 70%, #fff)`); }
  else { h.style.removeProperty('--gold'); h.style.removeProperty('--gold-bright'); }
  try { localStorage.setItem('vis', JSON.stringify(vis)); } catch (e) {}
}
function visPanel() {
  let p = $('#vis-panel');
  if (!p) {
    p = document.createElement('div'); p.id = 'vis-panel'; p.className = 'vis-panel'; p.hidden = true;
    p.innerHTML = `<div class="vis-box" role="dialog" aria-label="Personalizar visual"><button class="vis-x" type="button" aria-label="Fechar">×</button><small class="eyebrow">PERSONALIZAR</small><h3>Seu visual</h3>
<h4>Tema</h4><div class="vis-themes">${VIS_TEMAS.map(([id, n, c]) => `<button type="button" data-t="${id}" style="--sw:${c}"><i></i>${n}</button>`).join('')}</div>
<h4>Cor de destaque</h4><div class="vis-row"><input type="color" id="vis-cor" value="#9b78c4"><button type="button" class="secondary" id="vis-cor-reset">Usar cor do tema</button></div>
<h4>Emblema</h4><div class="vis-emb">${VIS_EMB.map(e => `<button type="button" data-e="${e}">${e}</button>`).join('')}</div>
<h4>Frase do perfil</h4><input id="vis-frase" maxlength="80" placeholder="Ex.: Louvado seja o sol!" class="deck-search">
<button class="primary" id="vis-save" type="button">Salvar no meu perfil</button><small class="muted" id="vis-msg"></small></div>`;
    document.body.appendChild(p);
    p.addEventListener('click', (e) => {
      if (e.target === p || e.target.closest('.vis-x')) { p.hidden = true; return; }
      const t = e.target.closest('[data-t]'), em = e.target.closest('[data-e]');
      if (t) visSet({tema: t.dataset.t}); if (em) visSet({emblema: em.dataset.e});
      if (e.target.id === 'vis-cor-reset') visSet({cor: ''});
      if (e.target.id === 'vis-save') visSave();
      visMark();
    });
    $('#vis-cor').addEventListener('input', (e) => { visSet({cor: e.target.value}); visMark(); });
    $('#vis-frase').addEventListener('input', (e) => { vis.frase = e.target.value; });
  }
  $('#vis-frase').value = vis.frase || ''; if (vis.cor) $('#vis-cor').value = vis.cor; visMark(); return p;
}
function visMark() {
  document.querySelectorAll('#vis-panel [data-t]').forEach(b => b.classList.toggle('on', b.dataset.t === vis.tema));
  document.querySelectorAll('#vis-panel [data-e]').forEach(b => b.classList.toggle('on', b.dataset.e === vis.emblema));
}
async function visSave() {
  const msg = $('#vis-msg');
  if (!currentUser) { msg.textContent = 'Aplicado neste navegador. Entre com Discord para salvar no perfil.'; return; }
  try {
    const r = await fetch('/api/hub/prefs', {method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({tema: vis.tema, cor: vis.cor || '', frase: vis.frase || '', emblema: vis.emblema})});
    const d = await r.json(); msg.textContent = r.ok ? 'Salvo! Aparece no seu perfil e no ranking.' : (d.error || 'Falha ao salvar.');
    if (r.ok) loadHub();
  } catch (e) { msg.textContent = 'Sem conexão com o servidor.'; }
}
$('#vis-open')?.addEventListener('click', () => { visPanel().hidden = false; });

/* ===== NARABOT PRO · JS visual (sem mexer na lógica do jogo) ===== */
(() => {
  const CB = 'data:image/svg+xml,data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 420 620%22%3E%3Cdefs%3E%3ClinearGradient id=%22g%22 x1=%220%22 y1=%220%22 x2=%221%22 y2=%221%22%3E%3Cstop offset=%220%22 stop-color=%22%23fff3c9%22/%3E%3Cstop offset=%22.55%22 stop-color=%22%23d9ae62%22/%3E%3Cstop offset=%221%22 stop-color=%22%238a6a2e%22/%3E%3C/linearGradient%3E%3ClinearGradient id=%22b%22 x1=%220%22 y1=%220%22 x2=%220%22 y2=%221%22%3E%3Cstop offset=%220%22 stop-color=%22%231d2650%22/%3E%3Cstop offset=%221%22 stop-color=%22%230a0d1c%22/%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width=%22420%22 height=%22620%22 fill=%22url(%23b)%22/%3E%3Crect x=%2218%22 y=%2218%22 width=%22384%22 height=%22584%22 rx=%2214%22 fill=%22none%22 stroke=%22url(%23g)%22 stroke-width=%225%22/%3E%3Crect x=%2238%22 y=%2238%22 width=%22344%22 height=%22544%22 rx=%228%22 fill=%22none%22 stroke=%22%23d9ae62%22 stroke-opacity=%22.35%22/%3E%3Ccircle cx=%22210%22 cy=%22310%22 r=%2296%22 fill=%22none%22 stroke=%22url(%23g)%22 stroke-width=%224%22 stroke-dasharray=%228 9%22/%3E%3Cpath d=%22M210 190 230 290 330 310 230 330 210 430 190 330 90 310 190 290z%22 fill=%22url(%23g)%22/%3E%3C/svg%3E', AV = 'data:image/svg+xml,data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 120 120%22%3E%3Crect width=%22120%22 height=%22120%22 fill=%22%23141a33%22/%3E%3Ccircle cx=%2260%22 cy=%2246%22 r=%2222%22 fill=%22%236c86b3%22/%3E%3Cpath d=%22M16 120c0-28 20-44 44-44s44 16 44 44z%22 fill=%22%236c86b3%22/%3E%3C/svg%3E';
  // Imagem quebrada -> arte de reserva (cartas e avatares)
  document.addEventListener('error', (e) => {
    const i = e.target; if (!i || i.tagName !== 'IMG' || i.dataset.fb) return; i.dataset.fb = 1;
    i.src = (i.classList.contains('hub-av') || i.closest('.avatar,.player-chip,.rank-row,.pod')) ? AV : CB;
  }, true);
  // Subtítulo explicativo sob o título de cada aba
  const SUB = {'Início':'Resumo do servidor, seu perfil e a Nara','Comunidade':'Ranking e membros do servidor','Arena':'Desafie um rival e dispute o melhor de três','Deck e Coleção':'Monte seu exército e gerencie suas cartas','Catálogo':'Mods e jogos compartilhados pela comunidade','Mercado e Drops':'Ganhe, abra pacotes e acompanhe recompensas','Ateliê':'Crie a arte oficial das cartas','Meu Portal':'Perfil, santuário, loja, envios e contribuições','Moderação':'Fila de aprovação e notícias','Guia':'Facções, regras e recompensas'};
  const h = document.getElementById('page-title');
  if (h) {
    const p = document.createElement('p'); p.className = 'page-sub'; h.after(p);
    const up = () => { p.textContent = SUB[h.textContent.trim()] || ''; };
    new MutationObserver(up).observe(h, {childList: true, characterData: true, subtree: true}); up();
  }
  // Descrições de rótulo (acessibilidade) nas abas
  document.querySelectorAll('.nav[data-tab]').forEach(b => b.setAttribute('aria-label', (b.querySelector('span') || b).textContent.trim()));
})();

/* ===== NARABOT PRO · Catálogo de jogos e mods ===== */
(() => {
  let kind = 'ports', timer = 0, seq = 0;
  const grid = $('#cat-grid'), cnt = $('#cat-count');
  const safeUrl = (u) => /^https?:\/\//i.test(u || '') ? u : '';
  const card = (it) => {
    // image_url aponta para a rota do portal que serve capas locais do catálogo.
    const img = it.image_url || safeUrl(it.image);
    const tag = kind === 'ports' ? (it.platform || 'Port') : 'Mod';
    const sub = kind === 'ports' ? '' : `<small class="cat-game">${escapeHTML(it.game || '')}</small>`;
    const link = safeUrl(it.link), tut = safeUrl(it.tutorial), iso = safeUrl(it.iso);
    const extras = Array.isArray(it.other_links) ? it.other_links : [];
    const actions = [
      link ? `<a class="primary linkbtn" href="${escapeHTML(link)}" target="_blank" rel="noopener noreferrer">${kind === 'ports' ? 'Baixar' : 'Ver mod'}</a>` : '',
      iso ? `<a class="secondary linkbtn" href="${escapeHTML(iso)}" target="_blank" rel="noopener noreferrer">ISO original</a>` : '',
      tut ? `<a class="secondary linkbtn" href="${escapeHTML(tut)}" target="_blank" rel="noopener noreferrer">Tutorial</a>` : '',
      ...extras.map(x => {
        const url = safeUrl(x.url);
        return url ? `<a class="secondary linkbtn" href="${escapeHTML(url)}" target="_blank" rel="noopener noreferrer">${escapeHTML(x.name || 'Link adicional')}</a>` : '';
      })
    ].filter(Boolean).join('');
    return `<article class="cat-card"><div class="cat-img"${img ? ` style="background-image:url('${escapeHTML(img)}')"` : ''}>${img ? '' : `<span>${escapeHTML((it.name || '?')[0].toUpperCase())}</span>`}<em class="cat-tag">${escapeHTML(tag)}</em></div><div class="cat-body">${sub}<h4>${escapeHTML(it.name || 'Sem nome')}</h4><p>${escapeHTML(it.description || 'Sem descrição.')}</p><div class="cat-actions">${actions}</div></div></article>`;
  };
  async function loadCatalog() {
    const my = ++seq, q = ($('#cat-search').value || '').trim();
    grid.innerHTML = '<p class="muted">Carregando catálogo...</p>';
    try {
      const r = await fetch(`/api/portal/catalog?kind=${kind}&q=${encodeURIComponent(q)}`, {credentials: 'same-origin', cache: 'no-store'});
      const d = await r.json(); if (my !== seq) return;
      if (!r.ok) throw new Error(d.error || 'Falha ao carregar.');
      const items = d.items || [];
      cnt.textContent = `${number(items.length)} ${items.length === 1 ? 'item' : 'itens'}`;
      grid.innerHTML = items.length ? items.map(card).join('') : `<div class="cat-empty"><b>Nada encontrado</b><p class="muted">${q ? 'Tente outra busca.' : 'O catálogo ainda está vazio. Seja o primeiro a sugerir um item!'}</p></div>`;
    } catch (e) { if (my === seq) { cnt.textContent = ''; grid.innerHTML = `<div class="cat-empty"><b>Não foi possível carregar</b><p class="muted">${escapeHTML(e.message)}</p></div>`; } }
  }
  const setKind = (k) => {
    kind = k; document.querySelectorAll('#cat-seg button').forEach(b => b.classList.toggle('on', b.dataset.kind === k));
    $('#cs-plat-l').hidden = k !== 'ports'; $('#cs-name').placeholder = k === 'ports' ? 'Nome do port' : 'Nome do mod'; loadCatalog();
  };
  document.querySelectorAll('#cat-seg button').forEach(b => b.addEventListener('click', () => setKind(b.dataset.kind)));
  $('#cat-search').addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(loadCatalog, 300); });
  document.addEventListener('click', (e) => { if (e.target.closest('[data-tab="catalog"],[data-goto="catalog"]')) loadCatalog(); });
  $('#cs-send').addEventListener('click', async (ev) => {
    const btn = ev.currentTarget, v = (id) => $(id).value.trim();
    const body = {game: v('#cs-game'), name: v('#cs-name'), link: v('#cs-link'), description: v('#cs-desc'), platform: v('#cs-plat') || 'Outra'};
    if (!body.game || !body.name || !/^https?:\/\//i.test(body.link)) return showNotice('Preencha jogo, nome e um link http/https válido.', 'error');
    btn.disabled = true;
    try {
      const r = await fetch(`/api/portal/catalog/${kind}`, {method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
      const d = await r.json().catch(() => ({}));
      if (r.status === 401) return showNotice('Entre com sua conta Discord para sugerir itens.', 'error');
      if (!r.ok) return showNotice(d.error || 'Não foi possível enviar.', 'error');
      showNotice('Sugestão enviada! Ela aparece no catálogo após a aprovação da moderação.', 'success');
      ['#cs-game', '#cs-name', '#cs-link', '#cs-desc', '#cs-plat'].forEach(i => $(i).value = '');
      $('#cat-suggest').open = false;
    } catch (e) { showNotice('Erro de conexão. Tente novamente.', 'error'); } finally { btn.disabled = false; }
  });
})();

/* ===== NARABOT PRO · Portal (perfil, santuário, loja, envios, contribuições, notificações, moderação) ===== */
(() => {
  const E = escapeHTML, $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const ST = {pending: ['Pendente', 'warn'], approved: ['Aprovado', 'ok'], rejected: ['Rejeitado', 'bad'], changes_requested: ['Ajustes pedidos', 'warn']};
  const KIND = {platina: 'Platina', zerado: 'Zerado', run: 'Run Soulslike', ports: 'Port', mods: 'Mod', lore: 'Lore', guide: 'Guia', correction: 'Correção', idea: 'Ideia', faq: 'FAQ', challenge: 'Desafio', game_suggestion: 'Sugestão de jogo'};
  const THEMES = ['Ouro', 'Prata', 'Safira', 'Esmeralda', 'Rubi', 'Ametista'];
  const fdate = (s) => { const d = new Date(String(s || '').replace(' ', 'T')); return isNaN(d) ? '' : d.toLocaleDateString('pt-BR'); };
  const login = '<div class="pt-empty"><b>Entre para continuar</b><p class="muted">Conecte sua conta Discord para usar esta página.</p><a class="primary linkbtn" href="/auth/discord/login">Entrar com Discord</a></div>';
  const empty = (t, s = '') => `<div class="pt-empty"><b>${E(t)}</b>${s ? `<p class="muted">${E(s)}</p>` : ''}</div>`;
  const chip = (st) => { const [t, c] = ST[st] || [st || '—', 'warn']; return `<span class="pt-chip ${c}">${E(t)}</span>`; };
  async function api(path, opt = {}) {
    try {
      const o = {credentials: 'same-origin', cache: 'no-store', ...opt};
      if (opt.json !== undefined) { o.method = o.method || 'POST'; o.headers = {'Content-Type': 'application/json'}; o.body = JSON.stringify(opt.json); delete o.json; }
      const r = await fetch(path, o); let d = null; const t = await r.text();
      try { d = JSON.parse(t); } catch (e) { d = {error: t.slice(0, 160)}; }
      return {ok: r.ok, status: r.status, data: d || {}};
    } catch (e) { return {ok: false, status: 0, data: {error: 'Erro de conexão.'}}; }
  }
  const fail = (r) => showNotice(r.status === 401 ? 'Entre com sua conta Discord.' : (r.data.error || 'Não foi possível concluir.'), 'error');
  const uid = () => currentUser && currentUser.id;
  const field = (l, id, ph = '', ml = 200, cls = '') => `<label class="${cls}">${l}<input id="${id}" maxlength="${ml}" placeholder="${E(ph)}"></label>`;
  const area = (l, id, ph = '', ml = 1000, rows = 4) => `<label class="wide">${l}<textarea id="${id}" rows="${rows}" maxlength="${ml}" placeholder="${E(ph)}"></textarea></label>`;
  const V = (id) => ($('#' + id) || {value: ''}).value.trim();
  let players = null;
  const loadPl = async () => { if (!players) { const r = await api('/api/players'); players = r.ok ? (r.data.players || []) : []; } return players; };
  const nameOf = (id) => ((players || []).find(p => String(p.id) === String(id)) || {}).name || `Membro ${id}`;

  /* ---------- navegação interna ---------- */
  const loaders = {};
  function sub(root, name) {
    $$(`#${root} .pt-pill`).forEach(b => b.classList.toggle('on', b.dataset.p === name));
    $$(`#${root} .pt-pane`).forEach(p => p.hidden = p.dataset.p !== name);
    loaders[name] && loaders[name]();
  }
  $$('.pt-nav').forEach(nav => nav.addEventListener('click', (e) => { const b = e.target.closest('.pt-pill'); if (b) sub(nav.closest('.tab').id, b.dataset.p); }));
  document.addEventListener('click', (e) => {
    const t = e.target.closest('[data-tab="portal"],[data-goto="portal"],[data-tab="admin"]'); if (!t) return;
    const root = (t.dataset.tab || t.dataset.goto) === 'admin' ? 'tab-admin' : 'tab-portal';
    const cur = $$(`#${root} .pt-pill.on`)[0]; sub(root, cur ? cur.dataset.p : $(`#${root} .pt-pill`).dataset.p);
  });

  /* ---------- PERFIL ---------- */
  const THEME_C = {Ouro: ['#d9ae62', 'Brasas douradas'], Prata: ['#c8d2dc', 'Neve de prata'], Safira: ['#5b8def', 'Bolhas do abismo'], Esmeralda: ['#4fcf8a', 'Vaga-lumes'], Rubi: ['#e0463a', 'Chamas rubras'], Ametista: ['#a98bff', 'Estrelas místicas']};
  const LINKS = [['perfil', '🎮', 'Steam / PSN / Xbox'], ['youtube', '▶️', 'YouTube'], ['twitch', '📺', 'Twitch'], ['site', '🌐', 'Site / Portfólio']];
  loaders.profile = async () => {
    const box = $('#pt-profile'); if (!uid()) return box.innerHTML = login;
    const [r, sr] = await Promise.all([api('/api/portal/profile'), api(`/api/portal/sanctuaries/${uid()}`), loadPl()]);
    if (!r.ok) return box.innerHTML = empty('Não foi possível carregar o perfil', r.data.error);
    const p = r.data.profile || {}; let links = {}; try { links = typeof p.links === 'string' ? JSON.parse(p.links || '{}') : (p.links || {}); } catch (e) {}
    const d = sr.ok ? sr.data : {}, s = d.summary || {}, rk = rankOf(s), nm = $('#profile-name').textContent || 'Seu nome';
    const pl = (players || []).find(x => String(x.id) === String(uid())) || {}, pr = PRES[pl.web_online ? 'on' : pl.discord_presence] || PRES.on;
    const num = {platinas: +s.platinas || 0, zerados: +s.zerados || 0, runs: +s.runs || 0, media_nota: +s.media_nota || 0};
    const got = BADGES.filter(b => b[3](num, d));
    const inp = (id, lab, ph, ml, ic) => `<label class="pf-f"><span>${ic ? `<em>${ic}</em>` : ''}${lab}<small class="pf-cnt" data-for="${id}"></small></span><input id="${id}" maxlength="${ml}" placeholder="${E(ph)}" autocomplete="off"></label>`;
    const sw = Object.entries(THEME_C).map(([t, [c, ds]]) => `<button type="button" class="pf-sw" data-t="${t}" style="--c:${c}"><i></i><b>${t}</b><small>${ds}</small></button>`).join('');
    box.innerHTML = `<div class="pf"><div class="pf-grid">
      <aside class="pf-side"><small class="pf-lab">✦ Pré-visualização ao vivo</small>
        <div class="pf-card" id="pf-card"><div class="pf-banner"><div class="pf-rays"></div><div class="pf-temple"></div></div>
          <div class="pf-av"><div class="pf-av-in"><span>${E(nm[0] || '?').toUpperCase()}</span>${pl.avatar ? `<img src="${E(pl.avatar)}" alt="" onerror="this.remove()">` : ''}</div><i class="sx-pres ${pr[0]}"></i></div>
          <div class="pf-body"><div class="pf-nrow"><h3>${E(nm)}</h3><span class="pf-rank">${rk.cur[2]} ${E(rk.cur[1])}</span></div>
            <p class="pf-quote" id="pv-tag"></p>
            <div class="pf-hr"></div><small class="pf-h">SOBRE MIM</small><p class="pf-bio" id="pv-bio"></p>
            <div id="pv-act"></div>
            <small class="pf-h">INSÍGNIAS · ${got.length}/${BADGES.length}</small><div class="pf-bdg">${got.map(b => `<span title="${E(b[1])}">${b[0]}</span>`).join('') || '<em>Jogue, zere e conquiste para ganhar insígnias.</em>'}</div>
            <div id="pv-links" class="pf-lks"></div></div></div>
        <small class="pf-note">É assim que seu santuário aparece para os outros membros.</small></aside>
      <div class="pf-form">
        <section class="pf-sec"><h4><i>1</i>Identidade</h4>${inp('pf-tag', 'Frase de destaque', 'Uma frase que te define', 100, '💬')}${inp('pf-fav', 'Jogo favorito', 'Ex.: Elden Ring', 100, '🎮')}</section>
        <section class="pf-sec"><h4><i>2</i>Tema do santuário</h4><div class="pf-sws">${sw}</div><select id="pf-theme" hidden>${THEMES.map(t => `<option>${t}</option>`).join('')}</select></section>
        <section class="pf-sec"><h4><i>3</i>Inscrições</h4><label class="pf-f"><span><em>📜</em>Biografia<small class="pf-cnt" data-for="pf-bio"></small></span><textarea id="pf-bio" rows="5" maxlength="1000" placeholder="Conte um pouco sobre você e seus jogos..."></textarea></label></section>
        <section class="pf-sec"><h4><i>4</i>Portais</h4><div class="pf-lgrid">${LINKS.map(([k, ic, l]) => inp('pf-l-' + k, l, 'https://...', 250, ic)).join('')}</div><small class="pf-warn" id="pf-warn" hidden>Use links começando com https:// — os outros não aparecem no santuário.</small></section>
      </div></div>
      <div class="pf-bar"><span class="pf-dirty" id="pf-dirty" hidden>● alterações não salvas</span><div class="pt-actions"><button class="primary" id="pf-save" type="button">💾 Salvar perfil</button><button class="secondary" type="button" data-pt-go="sanctuary">🏛 Ver meu santuário</button></div></div></div>`;
    $('#pf-tag').value = p.tagline || ''; $('#pf-fav').value = p.fav_game || ''; $('#pf-bio').value = p.bio || '';
    const th = THEMES.includes(p.theme) ? p.theme : 'Ouro'; $('#pf-theme').value = th;
    LINKS.forEach(([k]) => $('#pf-l-' + k).value = links[k] || '');
    let dirty = false;
    const upd = () => {
      const t = $('#pf-theme').value, card = $('#pf-card'); card.className = `pf-card pt-th-${t}`;
      $$('.pf-sw', box).forEach(b => b.classList.toggle('on', b.dataset.t === t));
      $('#pv-tag').textContent = V('pf-tag') ? `“${V('pf-tag')}”` : 'Escreva uma frase que te define…';
      $('#pv-bio').textContent = V('pf-bio') || 'Sua biografia aparecerá aqui.';
      $('#pv-act').innerHTML = V('pf-fav') ? `<div class="sx-act pf-act"><div class="sx-act-ic">🎮</div><div><small>JOGO FAVORITO</small><b>${E(V('pf-fav'))}</b></div><span class="sx-eq"><i></i><i></i><i></i><i></i></span></div>` : '';
      let bad = false;
      $('#pv-links').innerHTML = LINKS.map(([k, ic, l]) => { const v = V('pf-l-' + k), el = $('#pf-l-' + k); const ok = !v || /^https?:\/\//.test(v); el.classList.toggle('bad', !ok); bad = bad || !ok; return v && ok ? `<span class="sx-portal">${ic} ${l.split(' ')[0]}</span>` : ''; }).join('');
      $('#pf-warn').hidden = !bad;
      $$('.pf-cnt', box).forEach(c => { const el = $('#' + c.dataset.for); c.textContent = `${el.value.length}/${el.maxLength}`; });
      $('#pf-dirty').hidden = !dirty;
    };
    box.querySelector('.pf-form').addEventListener('input', () => { dirty = true; upd(); });
    $$('.pf-sw', box).forEach(b => b.onclick = () => { $('#pf-theme').value = b.dataset.t; dirty = true; upd(); });
    upd(); dirty = false; $('#pf-dirty').hidden = true;
    $('#pf-save').onclick = async () => {
      const l = {}; LINKS.forEach(([k]) => { const v = V('pf-l-' + k); if (v) l[k] = v; });
      const s2 = await api('/api/portal/profile', {json: {tagline: V('pf-tag'), fav_game: V('pf-fav'), bio: V('pf-bio'), theme: $('#pf-theme').value, links: l}});
      if (s2.ok) { showNotice('Perfil salvo com sucesso.', 'success'); dirty = false; upd(); const c = $('#pf-card'); c.classList.add('saved'); setTimeout(() => c.classList.remove('saved'), 1200); } else fail(s2);
    };
  };
  document.addEventListener('click', (e) => { const g = e.target.closest('[data-pt-go]'); if (g) sub('tab-portal', g.dataset.ptGo); });

  /* ---------- SANTUÁRIO ---------- */
  let viewing = null;
  const HON = {respect: ['🛡', 'Respeito'], determination: ['🔥', 'Determinação'], greatness: ['👑', 'Grandeza']};
  /* ---------- SANTUÁRIO · templo, efeitos e render ---------- */
  const RANKS = [[0, 'Peregrino', '🕯'], [8, 'Iniciado', '🗝'], [25, 'Guardião', '🛡'], [60, 'Campeão', '⚔'], [120, 'Lenda', '👑']];
  const rankOf = (s) => {
    const pts = (+s.platinas || 0) * 3 + (+s.zerados || 0) * 2 + (+s.runs || 0); let i = 0;
    RANKS.forEach((r, k) => { if (pts >= r[0]) i = k; });
    const nx = RANKS[i + 1];
    return {pts, i, cur: RANKS[i], nx, pct: nx ? Math.round((pts - RANKS[i][0]) / (nx[0] - RANKS[i][0]) * 100) : 100};
  };
  const templeSVG = () => {
    const cols = [170, 300, 430, 770, 900, 1030].map(x => `<g class="sx-col"><rect x="${x - 34}" y="172" width="68" height="14" rx="2"/><rect x="${x - 26}" y="186" width="52" height="254"/><rect x="${x - 36}" y="440" width="72" height="12" rx="2"/><path class="fl" d="M${x - 13} 190V438M${x} 190V438M${x + 13} 190V438"/></g>`).join('');
    const tri = [...Array(12)].map((_, i) => `<path d="M${130 + i * 82} 138v14"/>`).join('');
    return `<svg class="sx-temple" viewBox="0 0 1200 520" preserveAspectRatio="xMidYMax slice" aria-hidden="true"><defs>
      <linearGradient id="sxStone" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="color-mix(in srgb,var(--tc) 35%,#2a3050)"/><stop offset="1" stop-color="#0a0d1c"/></linearGradient>
      <radialGradient id="sxDoor" cx=".5" cy="1" r=".95"><stop offset="0" stop-color="var(--tc2)" stop-opacity=".95"/><stop offset=".45" stop-color="var(--tc)" stop-opacity=".35"/><stop offset="1" stop-color="#05060d" stop-opacity=".95"/></radialGradient></defs>
      <g fill="url(#sxStone)" stroke="var(--tc)" stroke-opacity=".55" stroke-width="1.5">
      <polygon points="100,122 600,16 1100,122"/><polygon points="170,118 600,30 1030,118" fill="#05060d" fill-opacity=".55"/>
      <rect x="100" y="122" width="1000" height="12"/><rect x="110" y="134" width="980" height="22"/><rect x="110" y="156" width="980" height="16"/>
      ${cols}
      <rect x="120" y="452" width="960" height="18"/><rect x="80" y="470" width="1040" height="20"/><rect x="40" y="490" width="1120" height="30"/></g>
      <g stroke="var(--tc)" stroke-opacity=".5" stroke-width="3" fill="none">${tri}</g>
      <circle class="sx-oculus" cx="600" cy="82" r="18" fill="var(--tc2)"/>
      <path class="sx-doorp" d="M440 452V268Q440 188 600 188Q760 188 760 268V452Z" fill="url(#sxDoor)" stroke="var(--tc2)" stroke-width="2"/>
      <path d="M462 452V272Q462 208 600 208Q738 208 738 272V452" fill="none" stroke="var(--tc2)" stroke-opacity=".5" stroke-width="1.5"/></svg>`;
  };
  const flameHTML = (c) => {
    const f = Math.min(1, .28 + Math.log2(1 + c) / 5).toFixed(2);
    return `<span class="sx-brazier" style="--f:${f}"><i class="sx-fl a"></i><i class="sx-fl b"></i><i class="sx-fl c"></i><i class="sx-bowl"></i><i class="sx-leg"></i></span>`;
  };
  function sxFx(root) {
    const sc = root.querySelector('.sx'); if (!sc) return;
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
    const fmt = (el, v) => { el.textContent = (+v).toFixed(+el.dataset.dec || 0); };
    const countUp = (el) => {
      const n = parseFloat(el.dataset.n); if (isNaN(n)) return;
      if (reduce) return fmt(el, n);
      const t0 = performance.now(), D = 1200;
      const f = (t) => { const k = Math.min(1, (t - t0) / D); fmt(el, n * (1 - Math.pow(1 - k, 3))); if (k < 1) requestAnimationFrame(f); };
      requestAnimationFrame(f);
    };
    const reveal = (el) => { el.classList.add('in'); el.querySelectorAll('[data-n]').forEach(countUp); };
    sc.classList.add('sx-js');
    const io = 'IntersectionObserver' in window ? new IntersectionObserver((es) => es.forEach(e => { if (e.isIntersecting) { reveal(e.target); io.unobserve(e.target); } }), {threshold: .12}) : null;
    sc.querySelectorAll('.sx-rv').forEach(el => io ? io.observe(el) : reveal(el));
    const hero = sc.querySelector('.sx-hero');
    if (hero && !reduce) hero.addEventListener('pointermove', (e) => {
      const r = hero.getBoundingClientRect();
      hero.style.setProperty('--mx', ((e.clientX - r.left) / r.width - .5).toFixed(3));
      hero.style.setProperty('--my', ((e.clientY - r.top) / r.height - .5).toFixed(3));
    });
    const share = sc.querySelector('#sx-share');
    if (share) share.onclick = async () => { try { await navigator.clipboard.writeText(share.dataset.t); showNotice('Cartão copiado! Cole no Discord.', 'success'); } catch (e) { showNotice('Não foi possível copiar.', 'error'); } };
    const av = sc.querySelector('.sx-av');
    sc.querySelectorAll('.pt-honor:not(:disabled)').forEach(b => b.addEventListener('click', () => b.classList.add('lit'), true));
    const cv = sc.querySelector('.sx-embers'); if (!cv || reduce) return;
    const mode = (sc.className.match(/pt-th-(\w+)/) || [])[1] || 'Ouro';
    const CFG = {Ouro: {n: 55, d: -1, sz: [.6, 2.8], sp: [.6, 2.2], k: 'dot'}, Prata: {n: 70, d: 1, sz: [.8, 2.6], sp: [.3, 1], k: 'dot'}, Safira: {n: 28, d: -1, sz: [3, 9], sp: [.4, 1.1], k: 'ring'}, Esmeralda: {n: 38, d: 0, sz: [1.4, 3.2], sp: [.2, .5], k: 'fly'}, Rubi: {n: 80, d: -1, sz: [.8, 3.4], sp: [1.2, 3.2], k: 'dot'}, Ametista: {n: 34, d: 0, sz: [3, 8], sp: [0, 0], k: 'star'}};
    const C = CFG[mode] || CFG.Ouro, rnd = (a, b) => a + Math.random() * (b - a);
    const ctx = cv.getContext('2d'), col = getComputedStyle(sc).getPropertyValue('--tc2').trim() || '#f3d69b';
    let W = 0, H = 0, dpr = 1; const bursts = [];
    const mk = (init) => ({x: Math.random(), y: init ? Math.random() : (C.d > 0 ? -.05 : 1.05), r: rnd(...C.sz), v: rnd(...C.sp) * .0007, s: rnd(0, 6.28), a: rnd(.35, 1)});
    const ps = [...Array(C.n)].map(() => mk(true));
    const burst = () => {
      const a = av.getBoundingClientRect(), c = cv.getBoundingClientRect(); if (!c.width) return;
      const x = (a.left + a.width / 2 - c.left) / c.width, y = (a.top + a.height / 2 - c.top) / c.height;
      for (let i = 0; i < 70; i++) { const g = rnd(0, 6.28), v = rnd(.002, .011); bursts.push({x, y, vx: Math.cos(g) * v, vy: Math.sin(g) * v * 1.3 - .004, l: 1, r: rnd(1, 3.2)}); }
    };
    if (av) av.onclick = () => { av.classList.remove('pop'); void av.offsetWidth; av.classList.add('pop'); burst(); };
    sc._burst = burst;
    const loop = () => {
      if (!cv.isConnected) return;
      if (!document.hidden && cv.clientWidth) {
        dpr = Math.min(2, window.devicePixelRatio || 1);
        if (W !== Math.round(cv.clientWidth * dpr)) { W = cv.width = Math.round(cv.clientWidth * dpr); H = cv.height = Math.round(cv.clientHeight * dpr); }
        ctx.clearRect(0, 0, W, H); ctx.fillStyle = col; ctx.strokeStyle = col; ctx.lineWidth = dpr;
        ps.forEach((p, i) => {
          p.s += C.k === 'star' ? .035 : .02;
          if (C.d) { p.y += C.d * p.v; p.x += Math.sin(p.s) * .0004; if (p.y < -.06 || p.y > 1.06) ps[i] = mk(false); }
          else if (C.k === 'fly') { p.x += Math.cos(p.s * .6 + i) * .0006; p.y += Math.sin(p.s * .5 + i) * .0005; if (p.x < 0 || p.x > 1) p.x = (p.x + 1) % 1; if (p.y < .05 || p.y > .95) p.s += 3; }
          else if (Math.sin(p.s) < -.98) { p.x = Math.random(); p.y = Math.random() * .8; }
          const x = p.x * W, y = p.y * H, r = p.r * dpr, tw = (Math.sin(p.s * (C.k === 'fly' ? 2 : 3)) + 1) / 2;
          if (C.k === 'dot') { ctx.globalAlpha = p.a * Math.max(0, Math.min(1, C.d < 0 ? p.y * 1.6 : (1.1 - p.y))) * (.6 + .4 * tw); ctx.beginPath(); ctx.arc(x, y, r, 0, 6.283); ctx.fill(); }
          else if (C.k === 'ring') { ctx.globalAlpha = .55 * p.a * Math.min(1, p.y * 2); ctx.beginPath(); ctx.arc(x, y, r, 0, 6.283); ctx.stroke(); }
          else if (C.k === 'fly') { const g = ctx.createRadialGradient(x, y, 0, x, y, r * 5); g.addColorStop(0, col); g.addColorStop(1, 'transparent'); ctx.globalAlpha = .25 + .75 * tw; ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r * 5, 0, 6.283); ctx.fill(); ctx.fillStyle = col; }
          else { ctx.globalAlpha = tw * p.a; ctx.beginPath(); ctx.moveTo(x, y - r * dpr); ctx.lineTo(x + r * .22 * dpr, y); ctx.lineTo(x, y + r * dpr); ctx.lineTo(x - r * .22 * dpr, y); ctx.closePath(); ctx.moveTo(x - r * dpr, y); ctx.lineTo(x, y + r * .22 * dpr); ctx.lineTo(x + r * dpr, y); ctx.lineTo(x, y - r * .22 * dpr); ctx.closePath(); ctx.fill(); }
        });
        for (let i = bursts.length - 1; i >= 0; i--) {
          const b = bursts[i]; b.x += b.vx; b.y += b.vy; b.vy += .00018; b.l -= .014;
          if (b.l <= 0) { bursts.splice(i, 1); continue; }
          ctx.globalAlpha = b.l; ctx.fillStyle = '#fff6d6'; ctx.beginPath(); ctx.arc(b.x * W, b.y * H, b.r * dpr * b.l, 0, 6.283); ctx.fill();
        }
        ctx.globalAlpha = 1; ctx.fillStyle = col;
      }
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }
  const sxTitle = (t) => `<h4 class="sx-title"><i></i><span>${t}</span><i></i></h4>`;
  const PRES = {online: ['on', 'Online no Discord'], idle: ['idle', 'Ausente'], dnd: ['dnd', 'Não perturbe'], offline: ['off', 'Offline'], on: ['on', 'Online no site']};
  const BADGES = [
    ['🥉', 'Primeira Platina', 'Conquiste 1 platina', (s) => s.platinas >= 1],
    ['🏆', 'Caçador de Platinas', 'Conquiste 10 platinas', (s) => s.platinas >= 10],
    ['💎', 'Lenda das Platinas', 'Conquiste 50 platinas', (s) => s.platinas >= 50],
    ['🎯', 'Zerador Implacável', 'Zere 25 jogos', (s) => s.zerados >= 25],
    ['💀', 'Alma Soulslike', 'Registre 10 runs', (s) => s.runs >= 10],
    ['🔍', 'Olhar Crítico', 'Nota média 8+ com 5 jogos zerados', (s) => s.zerados >= 5 && s.media_nota >= 8],
    ['⭐', 'Estrela do Servidor', 'Tenha 25 seguidores', (s, d) => d.followers >= 25],
    ['🔥', 'Honrado pelos Pares', 'Receba 20 honrarias', (s, d) => Object.values(d.honors || {}).reduce((a, b) => a + (+b || 0), 0) >= 20],
    ['🕯', 'Casa Cheia', 'Receba 5 recados no mural', (s, d) => (d.messages || []).length >= 5]
  ];
  const renderSanctuary = (d, p, s, own, nm, links, sel) => {
    const rk = rankOf(s), pl = (players || []).find(x => String(x.id) === String(viewing)) || {};
    const pr = PRES[pl.web_online ? 'on' : pl.discord_presence] || PRES.offline;
    const num = {platinas: +s.platinas || 0, zerados: +s.zerados || 0, runs: +s.runs || 0, media_nota: +s.media_nota || 0};
    const runes = [['🏆', 'Platinas', s.platinas], ['🎯', 'Zerados', s.zerados], ['⚔', 'Runs', s.runs], ['⭐', 'Nota média', s.media_nota != null ? Number(s.media_nota) : null], ['👥', 'Seguidores', d.followers]]
      .map(([ic, k, v]) => `<div class="sx-rune"><em>${ic}</em><b ${v == null && k === 'Nota média' ? '' : `data-n="${+v || 0}" data-dec="${k === 'Nota média' ? 1 : 0}"`}>${v == null && k === 'Nota média' ? '—' : 0}</b><small>${k}</small></div>`).join('');
    const got = BADGES.map(([ic, t, h, f]) => [ic, t, h, !!f(num, d)]);
    const badges = got.map(([ic, t, h, ok]) => `<div class="sx-badge2 ${ok ? 'ok' : ''}" tabindex="0"><div class="hex"><span>${ok ? ic : '🔒'}</span></div><b>${E(t)}</b><small>${ok ? 'Conquistada' : E(h)}</small></div>`).join('');
    const hon = Object.entries(HON).map(([k, [i, l]]) => { const c = (d.honors || {})[k] || 0; return `<button class="pt-honor sx-altar" data-k="${k}" ${own ? 'disabled' : ''} type="button">${flameHTML(c)}<span class="sx-ic">${i}</span><b>${c}</b><small>${l}</small></button>`; }).join('');
    const lk = Object.entries(links).filter(([, v]) => /^https?:\/\//.test(v)).map(([k, v]) => `<a class="sx-portal" href="${E(v)}" target="_blank" rel="noopener noreferrer">${E(k)} <span>↗</span></a>`).join('');
    const msgs = (d.messages || []).map(m => `<div class="pt-msg sx-offer"><i class="sx-candle"></i><div class="sx-oh"><b>${E(nameOf(m.author_id))}</b><small>${fdate(m.created_at)}</small></div><p>${E(m.message)}</p>${own ? `<button class="text-btn" data-del="${m.id}" type="button">apagar</button>` : ''}</div>`).join('') || '<p class="muted sx-none">Nenhuma oferenda ainda. As velas aguardam o primeiro visitante.</p>';
    const card = `🏛️ **Santuário de ${nm}** — ${rk.cur[2]} ${rk.cur[1]}\n🏆 ${num.platinas} platinas · 🎯 ${num.zerados} zerados · ⚔ ${num.runs} runs${s.media_nota != null ? ` · ⭐ ${num.media_nota.toFixed(1)}` : ''}\n🎖 ${got.filter(g => g[3]).length}/${got.length} insígnias${p.fav_game ? ` · 🎮 ${p.fav_game}` : ''}\n> ${p.tagline || 'Entre no meu santuário!'}\n${location.origin}${location.pathname}`;
    return sel + `<div class="sx pt-th-${E(p.theme || 'Ouro')}">
    <section class="sx-hero">
      <div class="sx-sky"></div><div class="sx-rays"></div><div class="sx-stars"></div>
      ${templeSVG()}<canvas class="sx-embers"></canvas>
      <div class="sx-core">
        <small class="sx-eyebrow">${own ? '✦ SEU SANTUÁRIO ✦' : '✦ SANTUÁRIO ✦'}</small>
        <div class="sx-av" title="Clique!"><svg viewBox="0 0 200 200" aria-hidden="true"><circle class="r1" cx="100" cy="100" r="96"/><circle class="r2" cx="100" cy="100" r="86"/></svg><div class="sx-av-in"><span>${E(nm[0] || '?').toUpperCase()}</span>${pl.avatar ? `<img src="${E(pl.avatar)}" alt="" onerror="this.remove()">` : ''}</div><span class="sx-badge">${rk.cur[2]}</span><i class="sx-pres ${pr[0]}" title="${pr[1]}"></i></div>
        <div class="sx-rank">${E(rk.cur[1])}</div>
        <h3 class="sx-name">${E(nm)}</h3>
        <p class="sx-tag">“${E(p.tagline || 'Este jogador ainda não escreveu uma frase.')}”</p>
        <div class="sx-chips"><span class="sx-chip pres ${pr[0]}">${pr[1]}</span><span class="sx-chip">${rk.pts} pontos de glória</span><span class="sx-chip">🎖 ${got.filter(g => g[3]).length}/${got.length} insígnias</span></div>
        ${p.fav_game ? `<div class="sx-act"><div class="sx-act-ic">🎮</div><div><small>JOGO FAVORITO</small><b>${E(p.fav_game)}</b></div><span class="sx-eq"><i></i><i></i><i></i><i></i></span></div>` : ''}
        <div class="sx-lvl" title="${rk.nx ? `Faltam ${rk.nx[0] - rk.pts} pontos para ${E(rk.nx[1])}` : 'Nível máximo'}"><div><i style="width:${rk.pct}%"></i></div><small>${rk.nx ? `Próximo título: ${E(rk.nx[1])}` : 'Título máximo alcançado'}</small></div>
        <div class="sx-btns">${own ? '' : '<button class="primary sx-follow" id="sc-follow" type="button">Seguir</button>'}<button class="secondary sx-sharebtn" id="sx-share" type="button" data-t="${E(card)}">📋 Copiar para o Discord</button></div>
      </div>
    </section>
    <div class="sx-rv">${sxTitle('Runas de Conquista')}<div class="sx-runes">${runes}</div></div>
    <div class="sx-rv">${sxTitle('Salão de Insígnias')}<div class="sx-badges">${badges}</div></div>
    <div class="sx-rv">${sxTitle('Altares de Honra')}<div class="sx-altars pt-honors">${hon}</div>${own ? '' : '<small class="muted sx-hint">Acenda uma chama: você pode honrar este jogador uma vez por semana.</small>'}</div>
    <div class="sx-rv">${sxTitle('Inscrições')}<div class="sx-tablet"><p class="sx-bio">${E(p.bio || 'Nenhuma inscrição foi gravada nesta pedra.')}</p>${lk ? `<div class="sx-portals">${lk}</div>` : ''}</div></div>
    <div class="sx-rv">${sxTitle('Mural de Oferendas')}<div class="sx-offers pt-msgs">${msgs}</div>${own ? '' : `<div class="pt-form sx-leave"><label class="wide">Deixe uma oferenda<textarea id="gb-text" rows="2" maxlength="300" placeholder="Até 300 caracteres. Um recado por dia."></textarea></label><button class="primary" id="gb-send" type="button">Acender uma vela</button></div>`}</div>
    </div>`;
  };

  loaders.sanctuary = async (target) => {
    const box = $('#pt-sanctuary'); if (!uid()) return box.innerHTML = login;
    await loadPl(); viewing = String(target || viewing || uid());
    const r = await api(`/api/portal/sanctuaries/${viewing}`);
    const sel = `<div class="pt-pick"><input id="sc-search" class="deck-search" type="search" placeholder="Visitar o santuário de outro membro..." list="sc-list" autocomplete="off"><datalist id="sc-list">${players.slice(0, 200).map(p => `<option value="${E(p.name)}"></option>`).join('')}</datalist><button class="secondary" id="sc-go" type="button">Visitar</button>${viewing !== String(uid()) ? '<button class="secondary" id="sc-me" type="button">Meu santuário</button>' : ''}</div>`;
    if (!r.ok) { box.innerHTML = sel + empty('Santuário indisponível', r.data.error); }
    else {
      const d = r.data, p = d.profile || {}, s = d.summary || {}, own = d.is_owner; let links = {}; try { links = typeof p.links === 'string' ? JSON.parse(p.links || '{}') : (p.links || {}); } catch (e) {}
      const nm = own ? ($('#profile-name').textContent || 'Seu santuário') : nameOf(viewing);
      box.innerHTML = renderSanctuary(d, p, s, own, nm, links, sel); sxFx(box);
      $$('.pt-honor', box).forEach(b => b.onclick = async () => { const x = await api('/api/portal/sanctuaries/honor', {json: {user_id: Number(viewing), honor_key: b.dataset.k}}); x.ok ? (showNotice('Honraria enviada!', 'success'), loaders.sanctuary()) : fail(x); });
      const fo = $('#sc-follow'); if (fo) fo.onclick = async () => { const x = await api('/api/portal/community/follow', {json: {user_id: Number(viewing)}}); x.ok ? (showNotice(x.data.following ? 'Agora você segue este jogador.' : 'Você deixou de seguir.', 'success'), loaders.sanctuary()) : fail(x); };
      const gs = $('#gb-send'); if (gs) gs.onclick = async () => { const x = await api(`/api/portal/sanctuaries/${viewing}/guestbook`, {json: {message: V('gb-text')}}); x.ok ? (showNotice('Recado enviado.', 'success'), loaders.sanctuary()) : fail(x); };
      $$('[data-del]', box).forEach(b => b.onclick = async () => { const x = await api(`/api/portal/sanctuaries/${viewing}/guestbook?id=${b.dataset.del}`, {method: 'DELETE'}); x.ok ? loaders.sanctuary() : fail(x); });
    }
    const go = $('#sc-go'); if (go) go.onclick = () => { const q = V('sc-search').toLowerCase(), p = players.find(x => x.name.toLowerCase() === q) || players.find(x => x.name.toLowerCase().includes(q)); p ? loaders.sanctuary(p.id) : showNotice('Membro não encontrado.', 'error'); };
    const me = $('#sc-me'); if (me) me.onclick = () => loaders.sanctuary(uid());
  };

  /* ---------- LOJA ---------- */
  const TYPES = {};
  loaders.store = async () => {
    const box = $('#pt-store'); if (!uid()) return box.innerHTML = login;
    const r = await api('/api/portal/store'); if (!r.ok) return box.innerHTML = empty('Loja indisponível', r.data.error);
    const items = r.data.items || [], groups = {}; items.forEach(i => (groups[i.type] = groups[i.type] || []).push(i));
    const card = (i) => `<article class="pt-item ${i.equipped ? 'eq' : ''}"><div class="pt-emoji">${E(i.emoji || '🎁')}</div><h4>${E(i.name)}</h4><p>${E(i.description || '')}</p><div class="pt-meta"><span class="pt-chip">◈ ${number(i.price)}</span>${i.min_level > 1 ? `<span class="pt-chip warn">Nível ${i.min_level}+</span>` : ''}${i.owned ? '<span class="pt-chip ok">Seu</span>' : ''}</div>
      ${i.owned ? `<button class="secondary" data-a="${i.equipped ? 'unequip' : 'equip'}" data-i="${E(i.id)}" type="button">${i.equipped ? 'Desequipar' : 'Equipar'}</button>` : `<button class="primary" data-a="buy" data-i="${E(i.id)}" type="button">Comprar</button>`}</article>`;
    box.innerHTML = `<div class="pt-balance"><span>Seu saldo</span><b>◈ ${number(r.data.balance)}</b><small class="muted">Denários</small></div>` + (Object.entries(groups).map(([t, l]) => `<h4 class="pt-gt">${E(t)}</h4><div class="pt-store">${l.map(card).join('')}</div>`).join('') || empty('A loja está vazia'));
    $$('[data-a]', box).forEach(b => b.onclick = async () => { b.disabled = true; const x = await api('/api/portal/store/action', {json: {item: b.dataset.i, action: b.dataset.a}}); x.ok ? (showNotice(b.dataset.a === 'buy' ? 'Compra realizada!' : 'Atualizado.', 'success'), loaders.store(), loadAccount && 0) : (fail(x), b.disabled = false); });
  };

  /* ---------- ENVIOS (platina, zerado, run) ---------- */
  let sKind = 'platina', runOpts = null;
  const num = (id, l, mn, mx) => `<label>${l}<input id="${id}" type="number" min="${mn}" max="${mx}" placeholder="${mn}–${mx}"></label>`;
  function sForm() {
    const box = $('#pt-form'), run = sKind === 'run';
    const g = run ? `<label>Jogo<select id="sf-gid"><option value="">Selecione...</option>${(runOpts.games || []).map(x => `<option value="${x.id}">${E(x.name)}</option>`).join('')}</select></label><label>Desafio<select id="sf-cid"><option value="">Selecione...</option></select></label><label>Tempo (min)<input id="sf-min" type="number" min="1" placeholder="Ex.: 90"></label>${field('Build / estilo', 'sf-build', 'Opcional', 300)}`
      : `${field('Jogo', 'sf-game', 'Nome do jogo', 100)}${field('Plataforma', 'sf-plat', 'PC, PS5, Switch...', 40)}<label>${sKind === 'platina' ? 'Data da platina' : 'Data de conclusão'}<input id="sf-date" type="date"></label>`;
    box.innerHTML = `<div class="pt-form">${g}${num('sf-rate', 'Nota (opcional)', 1, 10)}${num('sf-diff', 'Dificuldade (opcional)', 1, 5)}${area('Comentário', 'sf-com', 'Algo para a moderação ou para a comunidade...', 500, 3)}<label class="wide">Comprovantes (até 5 imagens/vídeos)<input id="sf-files" type="file" multiple accept="image/*,video/*"></label><button class="primary" id="sf-send" type="button">Enviar para aprovação</button></div>`;
    if (run) $('#sf-gid').onchange = () => { const gid = Number($('#sf-gid').value); $('#sf-cid').innerHTML = '<option value="">Selecione...</option>' + (runOpts.challenges || []).filter(c => !c.game_id || c.game_id === gid).map(c => `<option value="${c.id}">${E(c.name)}</option>`).join(''); };
    $('#sf-send').onclick = async (ev) => {
      const fd = new FormData(), files = [...$('#sf-files').files].slice(0, 5);
      if (!files.length) return showNotice('Anexe ao menos um comprovante.', 'error');
      if (run) { const m = Number(V('sf-min')); fd.append('game_id', V('sf-gid')); fd.append('challenge_id', V('sf-cid')); fd.append('seconds', Math.round(m * 60)); fd.append('build', V('sf-build')); }
      else { fd.append('game', V('sf-game')); fd.append('platform', V('sf-plat')); fd.append('date', V('sf-date')); }
      fd.append('rating', V('sf-rate')); fd.append('difficulty', V('sf-diff')); fd.append('comment', V('sf-com')); files.forEach(f => fd.append('proofs', f));
      ev.currentTarget.disabled = true;
      const x = await api(run ? '/api/portal/runs' : `/api/portal/submit/${sKind}`, {method: 'POST', body: fd});
      $('#sf-send') && ($('#sf-send').disabled = false);
      if (x.ok) { showNotice('Envio registrado! Aguarde a aprovação da moderação.', 'success'); sForm(); loadMine(); } else fail(x);
    };
  }
  async function loadMine() {
    const box = $('#pt-mine'), r = await api('/api/portal/mine'); if (!r.ok) return box.innerHTML = '';
    const rows = (r.data.items || []).map(i => `<div class="pt-row"><span class="pt-chip">${E(KIND[i.kind] || i.kind)}</span><div><b>${E(i.game)}</b><small>${E(i.platform || '')} ${i.date ? '· ' + E(i.date) : ''}</small>${i.comment && i.status !== 'pending' ? `<small class="muted">${E(i.comment)}</small>` : ''}</div>${chip(i.status)}${i.status === 'pending' ? `<button class="text-btn" data-c="${i.kind}/${i.id}" type="button">cancelar</button>` : ''}</div>`).join('');
    box.innerHTML = `<h4 class="pt-gt">Meus envios</h4>${rows || empty('Você ainda não enviou nada', 'Seus envios e o status da aprovação aparecem aqui.')}`;
    $$('[data-c]', box).forEach(b => b.onclick = async () => { if (!confirm('Cancelar este envio?')) return; const x = await api(`/api/portal/mine/${b.dataset.c}`, {method: 'DELETE'}); x.ok ? loadMine() : fail(x); });
  }
  loaders.submit = async () => {
    const box = $('#pt-submit-body'); if (!uid()) { box.hidden = true; $('#pt-submit-login').innerHTML = login; return; }
    box.hidden = false; $('#pt-submit-login').innerHTML = '';
    if (!runOpts) { const r = await api('/api/portal/runs/options'); runOpts = r.ok ? r.data : {games: [], challenges: []}; }
    sForm(); loadMine();
  };
  $('#pt-kind').addEventListener('click', (e) => { const b = e.target.closest('button'); if (!b) return; sKind = b.dataset.k; $$('#pt-kind button').forEach(x => x.classList.toggle('on', x === b)); sForm(); });

  /* ---------- CONTRIBUIÇÕES ---------- */
  let cFilter = 'approved';
  const CK = ['guide', 'lore', 'idea', 'faq', 'correction', 'challenge', 'game_suggestion', 'run'];
  loaders.contrib = async () => {
    const box = $('#pt-contrib-list'); $$('#pt-cfilter button').forEach(b => b.classList.toggle('on', b.dataset.f === cFilter));
    await loadPl();
    let r; if (cFilter === 'fav') r = uid() ? await api('/api/portal/community/favorites') : {ok: false, status: 401, data: {}}; else r = await api(`/api/portal/contributions?${cFilter === 'mine' ? 'mine=1' : 'status=approved'}`);
    if (r.status === 401) return box.innerHTML = login; if (!r.ok) return box.innerHTML = empty('Não foi possível carregar', r.data.error);
    const items = r.data.items || [];
    box.innerHTML = items.map(c => c.title === undefined ? `<div class="pt-card"><small class="muted">Item salvo #${E(c.target_id)}</small></div>` : `<article class="pt-card pt-post"><div class="pt-meta"><span class="pt-chip">${E(KIND[c.kind] || c.kind)}</span>${c.game_name ? `<span class="pt-chip ok">${E(c.game_name)}</span>` : ''}${cFilter === 'mine' ? chip(c.status) : ''}<small class="muted">${E(nameOf(c.user_id))} · ${fdate(c.created_at)}</small></div><h4>${E(c.title)}</h4><p>${E(c.summary || String(c.content || '').slice(0, 220))}</p><div class="pt-actions">${[['like', '👍', 'Curtir'], ['useful', '💡', 'Útil'], ['respect', '🤝', 'Respeito']].map(([k, i, l]) => `<button class="secondary" data-r="${k}" data-id="${c.id}" title="${l}" type="button">${i} ${l}</button>`).join('')}<button class="secondary" data-bm="${c.id}" type="button">🔖 Salvar</button>${c.kind === 'challenge' && c.status === 'approved' ? `<button class="primary" data-j="${c.id}" type="button">⚔ Participar</button>` : ''}</div></article>`).join('') || empty('Nada por aqui ainda', cFilter === 'mine' ? 'Você ainda não enviou contribuições.' : 'Seja o primeiro a contribuir!');
    $$('[data-r]', box).forEach(b => b.onclick = async () => { const x = await api('/api/portal/community/interact', {json: {target_type: 'contribution', target_id: Number(b.dataset.id), reaction: b.dataset.r}}); x.ok ? showNotice(x.data.added ? 'Reação registrada.' : 'Reação removida.', 'success') : fail(x); });
    $$('[data-bm]', box).forEach(b => b.onclick = async () => { const x = await api('/api/portal/community/bookmark', {json: {target_type: 'contribution', target_id: Number(b.dataset.bm)}}); x.ok ? showNotice(x.data.saved ? 'Salvo nos favoritos.' : 'Removido dos favoritos.', 'success') : fail(x); });
    $$('[data-j]', box).forEach(b => b.onclick = async () => { const x = await api('/api/portal/community/challenge', {json: {contribution_id: Number(b.dataset.j), action: 'join'}}); x.ok ? showNotice('Participação atualizada.', 'success') : fail(x); });
  };
  $('#pt-cfilter').addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) { cFilter = b.dataset.f; loaders.contrib(); } });
  $('#pt-cform').innerHTML = `<div class="pt-form"><label>Tipo<select id="cf-kind">${CK.map(k => `<option value="${k}">${KIND[k]}</option>`).join('')}</select></label>${field('Jogo (opcional)', 'cf-game', 'Nome do jogo', 100)}${field('Título', 'cf-title', 'Título da contribuição', 120, 'wide')}${field('Resumo', 'cf-sum', 'Em uma frase', 500, 'wide')}${area('Conteúdo (mín. 20 caracteres)', 'cf-content', 'Escreva seu guia, lore, ideia...', 12000, 7)}${field('Fontes (opcional)', 'cf-src', 'Links ou referências', 1500, 'wide')}<button class="primary" id="cf-send" type="button">Enviar contribuição</button><small class="muted">Passa pela moderação antes de aparecer para todos.</small></div>`;
  $('#cf-send').onclick = async () => {
    const x = await api('/api/portal/contributions', {json: {kind: $('#cf-kind').value, game_name: V('cf-game'), title: V('cf-title'), summary: V('cf-sum'), content: V('cf-content'), sources: V('cf-src')}});
    if (x.ok) { showNotice('Contribuição enviada para aprovação!', 'success'); ['cf-game', 'cf-title', 'cf-sum', 'cf-content', 'cf-src'].forEach(i => $('#' + i).value = ''); cFilter = 'mine'; loaders.contrib(); } else fail(x);
  };

  /* ---------- NOTIFICAÇÕES ---------- */
  const NP = {approvals: 'Aprovações', rejections: 'Rejeições', levels: 'Subidas de nível', replies: 'Respostas', challenges: 'Desafios'};
  loaders.notif = async () => {
    const box = $('#pt-notif'); if (!uid()) return box.innerHTML = login;
    const r = await api('/api/portal/notifications'); if (!r.ok) return box.innerHTML = empty('Não foi possível carregar', r.data.error);
    const items = r.data.items || [], pr = r.data.preferences || {};
    box.innerHTML = `<div class="pt-grid2"><div class="pt-card"><div class="pt-head"><h4>Não lidas</h4>${items.length ? '<button class="text-btn" id="nt-all" type="button">Marcar todas como lidas</button>' : ''}</div>${items.map(n => `<div class="pt-row"><span class="pt-chip">${E(NP[n.category] || n.category || 'Aviso')}</span><div><b>${E(n.message)}</b><small>${fdate(n.created_at)}</small></div></div>`).join('') || empty('Tudo em dia', 'Você não tem notificações novas.')}</div>
    <div class="pt-card"><h4>O que você quer receber</h4>${Object.entries(NP).map(([k, l]) => `<label class="pt-switch"><span>${l}</span><input type="checkbox" data-k="${k}" ${pr[k] !== false ? 'checked' : ''}><i></i></label>`).join('')}</div></div>`;
    const all = $('#nt-all'); if (all) all.onclick = async () => { const x = await api('/api/portal/notifications', {json: {action: 'read_all'}}); x.ok ? loaders.notif() : fail(x); };
    $$('[data-k]', box).forEach(c => c.onchange = async () => { const x = await api('/api/portal/notifications', {json: {key: c.dataset.k, enabled: c.checked}}); x.ok ? showNotice('Preferência salva.', 'success') : (fail(x), c.checked = !c.checked); });
  };

  /* ---------- MODERAÇÃO ---------- */
  const isCatalog = (i) => i.kind === 'ports' || i.kind === 'mods';
  const isContrib = (i) => 'guild_id' in i || ('content' in i && 'title' in i);
  loaders.queue = async () => {
    const box = $('#ad-queue'); await loadPl();
    const r = await api('/api/portal/admin/queue'); if (!r.ok) return box.innerHTML = empty('Acesso restrito à moderação', r.data.error);
    const items = r.data.items || [];
    box.innerHTML = `<div class="pt-balance"><span>Na fila</span><b>${items.length}</b><small class="muted">itens aguardando revisão</small></div>` + (items.map(i => {
      const k = isContrib(i) ? 'contribution' : i.kind, title = i.title || i.game || i.name || '—', extra = i.challenge ? ` · ${i.challenge}` : i.platform ? ` · ${i.platform}` : '';
      const proofs = (i.proofs || []).concat(i.proof_url ? [{url: i.proof_url, filename: 'Comprovante'}] : []).filter(p => /^https?:\/\/|^\//.test(p.url || '')).map(p => `<a href="${E(p.url)}" target="_blank" rel="noopener noreferrer">${E(p.filename || 'Comprovante')}</a>`).join('');
      return `<div class="pt-card pt-q" data-k="${k}" data-id="${i.id}"><div class="pt-meta"><span class="pt-chip">${E(KIND[isContrib(i) ? 'guide' : i.kind] && !isContrib(i) ? KIND[i.kind] : (isContrib(i) ? 'Contribuição · ' + (KIND[i.kind] || i.kind) : i.kind))}</span><small class="muted">${E(nameOf(i.user_id || i.autor_id))} · ${fdate(i.created_at)}</small></div><h4>${E(title)}<small>${E(extra)}</small></h4>${i.summary || i.comment || i.build ? `<p class="muted">${E(i.summary || i.comment || i.build)}</p>` : ''}${proofs ? `<div class="pt-proofs">${proofs}</div>` : ''}<div class="pt-actions"><button class="primary" data-d="approved" type="button">Aprovar</button><button class="secondary" data-d="rejected" type="button">Rejeitar</button>${isCatalog(i) ? '' : '<button class="secondary" data-d="changes_requested" type="button">Pedir ajustes</button>'}</div></div>`;
    }).join('') || empty('Fila vazia', 'Nenhum item aguardando aprovação.'));
    $$('.pt-q [data-d]', box).forEach(b => b.onclick = async () => {
      const q = b.closest('.pt-q'), k = q.dataset.k, a = b.dataset.d; let note = '';
      if (a !== 'approved' && !isCatalog({kind: k})) { note = prompt('Observação para o membro (opcional):') || ''; }
      b.disabled = true;
      const x = isCatalog({kind: k}) ? await api(`/api/portal/catalog/${k}/${q.dataset.id}`, {json: {action: a}}) : await api(`/api/portal/admin/${k}/${q.dataset.id}`, {json: {action: a, note}});
      x.ok ? (showNotice('Decisão registrada.', 'success'), loaders.queue()) : (fail(x), b.disabled = false);
    });
  };
  loaders.news = async () => {
    const box = $('#ad-news'), r = await api('/api/portal/admin/news'); if (!r.ok) return box.innerHTML = empty('Acesso restrito à moderação', r.data.error);
    box.innerHTML = `<div class="pt-grid2"><div class="pt-card"><h4>Feeds monitorados</h4>${(r.data.feeds || []).map(f => `<div class="pt-row"><span class="pt-chip ${f.ativo ? 'ok' : 'warn'}">${f.ativo ? 'Ativo' : 'Pausado'}</span><div><b>${E(f.nome)}</b><small>${E(f.url)}</small></div><button class="text-btn" data-rm="${f.id}" type="button">remover</button></div>`).join('') || empty('Nenhum feed cadastrado')}</div><div class="pt-card"><h4>Adicionar feed RSS</h4><div class="pt-form">${field('Nome', 'nw-name', 'Ex.: IGN Brasil', 80, 'wide')}${field('URL do RSS (https)', 'nw-url', 'https://...', 500, 'wide')}<button class="primary" id="nw-add" type="button">Validar e adicionar</button><small class="muted">As notícias novas são publicadas pelo bot no canal configurado.</small></div></div></div>`;
    $('#nw-add').onclick = async (ev) => { ev.currentTarget.disabled = true; const x = await api('/api/portal/admin/news', {json: {action: 'add', name: V('nw-name'), url: V('nw-url')}}); x.ok ? (showNotice('Feed adicionado.', 'success'), loaders.news()) : (fail(x), $('#nw-add').disabled = false); };
    $$('[data-rm]', box).forEach(b => b.onclick = async () => { if (!confirm('Remover este feed?')) return; const x = await api('/api/portal/admin/news', {json: {action: 'remove', id: Number(b.dataset.rm)}}); x.ok ? loaders.news() : fail(x); });
  };

  /* ---------- Descobrir moderador (mostra a aba Moderação) ---------- */
  (async () => { await new Promise(r => setTimeout(r, 1200)); if (!uid()) return; const r = await api('/api/portal/admin/queue'); if (r.ok) { const n = $('#nav-admin'); if (n) n.hidden = false; } })();
  window.portalVisit = (id) => { document.querySelector('.nav[data-tab="portal"]').click(); setTimeout(() => sub('tab-portal', 'sanctuary') || loaders.sanctuary(id), 50); };
})();


// Recalcula a largura ótima das cartas quando o jogador redimensiona a janela.
window.addEventListener('resize', () => {
  const nextWidth = window.innerWidth;
  if (!currentGwentMatch || Math.abs(nextWidth - gwentLastViewportWidth) < 80) return;
  gwentLastViewportWidth = nextWidth;
  refreshGwentMatch();
}, {passive:true});


/* V20 — Arsenal de Relíquias: pré-seleção persistida no navegador. */
(() => {
  const relics = {
    reliquia_grande_runa_godrick: ['Grande Runa de Godrick','Lendária','Concede +1 de bônus a todas as unidades aliadas em campo.','Grande Runa'],
    reliquia_runa_nao_nascidos: ['Grande Runa dos Não Nascidos','Lendária','Purifica Geada e Podridão dos aliados e fortalece os purificados.','Grande Runa'],
    reliquia_runa_morte: ['Runa da Morte','Mítica','Corrói bônus positivos das unidades inimigas em cada fileira.','Grande Runa'],
    reliquia_noite_chama: ['Espada da Noite e da Chama','Lendária','Escolha entre a postura da Chama ou da Noite para atacar uma fileira inimiga.','Arma lendária'],
    reliquia_lamina_negra: ['Lâmina Negra','Mítica','Reduz o bônus de uma unidade inimiga; Escudo pode bloquear o golpe.','Arma lendária'],
    reliquia_algemas_margit: ['Algemas de Margit','Épica','Anula os bônus positivos de uma unidade inimiga.','Artefato']
  };
  const select = document.querySelector('#gwent-relic-select');
  const preview = document.querySelector('#gwent-relic-preview');
  const status = document.querySelector('#gwent-relic-status');
  if (!select || !preview) return;
  const key = 'narabot_gwent_relic_loadout_v20';
  const render = () => {
    const relic = relics[select.value];
    preview.innerHTML = relic
      ? `<div class="v52-relic-seal"><i>♜</i><span>${escapeHTML(relic[3])}</span></div><small>${escapeHTML(relic[1])} · ${escapeHTML(relic[3])}</small><b>${escapeHTML(relic[0])}</b><p>${escapeHTML(relic[2])}</p><span class="gwent-relic-equipped">PREPARADA</span>`
      : '<b>Nenhuma Relíquia selecionada</b><p>Você entrará sem Relíquia equipada.</p>';
    if (status) status.textContent = 'Relíquia selecionada. Salve o deck para registrar a escolha na sua conta.';
  };
  try { select.value = localStorage.getItem(key) || ''; } catch (_) {}
  render();
  select.addEventListener('change', () => {
    try { localStorage.setItem(key, select.value); } catch (_) {}
    render();
    if (typeof renderGwentBuilder === 'function') renderGwentBuilder();
  });
})();
