const $ = (selector) => document.querySelector(selector);
let collection = [];
let currentUser = null;
let savedDeck = [];
let selectedDeck = [];
let currentDuelId = null;
let duelRefreshHandle = null;
let duelSocket = null;

const text = (value, fallback = '—') => value === null || value === undefined || value === '' ? fallback : String(value);
const number = (value) => new Intl.NumberFormat('pt-BR').format(Number(value || 0));
const imageUrl = (card) => card.image_url || `/api/cards/${encodeURIComponent(card.id)}/image`;

function showNotice(message, kind = 'info') {
  const notice = $('#notice');
  notice.textContent = message;
  notice.className = `notice ${kind}`;
  notice.hidden = !message;
}

function showPage(page) {
  document.querySelectorAll('.page').forEach((element) => element.classList.toggle('show', element.id === page));
  document.querySelectorAll('.nav').forEach((button) => button.classList.toggle('active', button.dataset.page === page));
  $('#page-title').textContent = page === 'collection' ? 'Minha coleção' : page === 'deck' ? 'Meu deck' : page === 'duels' ? 'Meus duelos' : 'Visão geral';
  if (page === 'deck') loadDeck();
  if (page === 'duels') loadDuels();
}

document.querySelectorAll('[data-page]').forEach((button) => button.addEventListener('click', () => showPage(button.dataset.page)));
document.querySelectorAll('[data-go]').forEach((button) => button.addEventListener('click', () => showPage(button.dataset.go)));

function cardMarkup(card) {
  return `<button class="game-card" type="button" data-card-id="${escapeHTML(card.id)}">
    <div class="card-image-wrap"><img class="card-image" src="${escapeHTML(imageUrl(card))}" alt="${escapeHTML(card.nome)}" loading="lazy"><span class="quantity">×${number(card.quantidade)}</span></div>
    <div class="card-meta"><small class="rarity rarity-${raritySlug(card.raridade)}">${escapeHTML(text(card.raridade))}</small><b>${escapeHTML(text(card.nome))}</b><small>${escapeHTML(text(card.categoria))} · ${escapeHTML(text(card.tipo))}</small><span class="power">✦ ${number(card.poder)} poder</span></div>
  </button>`;
}

function escapeHTML(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
}
function raritySlug(value) { return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase(); }

function renderCollection() {
  const query = $('#search').value.trim().toLocaleLowerCase('pt-BR');
  const rarity = $('#rarity').value;
  const category = $('#category').value;
  const type = $('#type').value;
  const filtered = collection.filter((card) => {
    const searchable = `${card.nome || ''} ${card.habilidade || ''} ${card.descricao || ''} ${card.jogo_origem || ''}`.toLocaleLowerCase('pt-BR');
    return (!query || searchable.includes(query)) && (!rarity || card.raridade === rarity) && (!category || card.categoria === category) && (!type || card.tipo === type);
  });
  $('#collection-grid').innerHTML = filtered.length ? filtered.map(cardMarkup).join('') : '<div class="empty-state">Nenhuma carta corresponde aos filtros.</div>';
  $('#collection-total').textContent = `${filtered.length} de ${collection.length} cartas`;
}

function renderDashboard(data) {
  const summary = data.summary || {};
  $('#souls').textContent = number(summary.souls);
  $('#denarios').textContent = number(summary.denarios);
  $('#home-souls').textContent = number(summary.souls);
  $('#home-denarios').textContent = number(summary.denarios);
  $('#total-cards').innerHTML = `${number(summary.cards)} <i>cartas</i>`;
  $('#deck-cards').innerHTML = `${number(summary.deck_cards)} <i>cartas</i>`;
  $('#featured').innerHTML = collection.slice(0, 4).map(cardMarkup).join('') || '<div class="empty-state">Sua coleção ainda está vazia.</div>';
  const categories = [...new Set(collection.map((card) => card.categoria).filter(Boolean))].sort((a,b) => a.localeCompare(b, 'pt-BR'));
  $('#category').innerHTML = '<option value="">Todas as categorias</option>' + categories.map((value) => `<option>${escapeHTML(value)}</option>`).join('');
  renderCollection();
}

async function loadAccount() {
  try {
    const meResponse = await fetch('/api/me', { credentials: 'same-origin', cache: 'no-store' });
    if (!meResponse.ok) {
      currentUser = null;
      $('#profile-name').textContent = 'Visitante';
      $('#profile-status').textContent = 'Conecte sua conta Discord';
      $('#login-button').hidden = false;
      $('#logout-button').hidden = true;
      showNotice('Entre com sua conta Discord para visualizar suas cartas e recursos reais.');
      return;
    }
    const me = await meResponse.json();
    currentUser = me.user;
    $('#profile-name').textContent = 'Conta Discord';
    $('#profile-status').textContent = `ID ${text(currentUser?.id)}`;
    $('#login-button').hidden = true;
    $('#logout-button').hidden = false;
    const response = await fetch('/api/collection', { credentials: 'same-origin', cache: 'no-store' });
    if (!response.ok) throw new Error(response.status === 401 ? 'Sua sessão expirou. Entre novamente com Discord.' : 'Falha ao consultar a coleção.');
    const data = await response.json();
    collection = Array.isArray(data.collection) ? data.collection : [];
    renderDashboard(data);
    showNotice(`Coleção sincronizada: ${collection.length} cartas carregadas do SoulsBot.`, 'success');
  } catch (error) {
    showNotice(error.message || 'Não foi possível conectar ao servidor.', 'error');
  }
}

async function loadDeck() {
  if (!currentUser) return;
  const status = $('#deck-status');
  status.textContent = 'Sincronizando com o deck do Discord...';
  try {
    const response = await fetch('/api/deck', { credentials: 'same-origin', cache: 'no-store' });
    if (!response.ok) throw new Error(response.status === 401 ? 'Sua sessão expirou. Entre novamente com Discord.' : 'Não foi possível carregar o deck.');
    const data = await response.json();
    savedDeck = Array.isArray(data.deck) ? data.deck : [];
    selectedDeck = savedDeck.map(card => card.id);
    renderDeck();
    status.textContent = savedDeck.length === 5 ? 'Deck carregado. Ele é o mesmo utilizado nos duelos do Discord.' : 'Você ainda não tem um deck salvo. Escolha cinco cartas para montar seu deck.';
  } catch (error) { status.textContent = error.message; }
}

function deckValidation(cards) {
  if (cards.length > 5) return 'O deck aceita exatamente cinco cartas.';
  const cost = cards.reduce((sum, card) => sum + Number(card.custo || 0), 0);
  if (cost > 12) return `Custo ${cost}/12: remova uma carta para respeitar o limite.`;
  if (cards.filter(card => card.raridade === 'Lendária').length > 1) return 'O deck pode conter no máximo uma carta Lendária.';
  if (new Set(cards.map(card => card.id)).size !== cards.length) return 'Não é permitido repetir cartas.';
  return '';
}

function renderDeck() {
  const chosen = selectedDeck.map(id => collection.find(card => card.id === id)).filter(Boolean);
  const cost = chosen.reduce((sum, card) => sum + Number(card.custo || 0), 0);
  const error = deckValidation(chosen);
  $('#deck-count').textContent = `${chosen.length}/5 cartas`;
  $('#deck-grid').innerHTML = Array.from({length:5}, (_, index) => {
    const card = chosen[index];
    return card ? `<article class="deck-slot"><img src="${escapeHTML(imageUrl(card))}" alt="${escapeHTML(card.nome)}"><div><b>${escapeHTML(card.nome)}</b><small>${escapeHTML(card.raridade)} · custo ${number(card.custo)}</small><button type="button" data-remove-deck="${escapeHTML(card.id)}">Remover</button></div></article>` : `<div class="deck-slot empty-slot"><span>${index + 1}</span><small>Espaço disponível</small></div>`;
  }).join('');
  $('#deck-summary').textContent = `Cartas: ${chosen.length}/5 · Custo: ${cost}/12 · Lendárias: ${chosen.filter(card => card.raridade === 'Lendária').length}/1` + (error ? ` · ${error}` : '');
  $('#save-deck').disabled = chosen.length !== 5 || Boolean(error) || JSON.stringify(selectedDeck) === JSON.stringify(savedDeck.map(card => card.id));
  const query = ($('#deck-search').value || '').trim().toLocaleLowerCase('pt-BR');
  const selected = new Set(selectedDeck);
  const available = collection.filter(card => !selected.has(card.id) && (!query || card.nome.toLocaleLowerCase('pt-BR').includes(query)));
  $('#deck-available').innerHTML = available.map(card => `<article class="available-card"><img src="${escapeHTML(imageUrl(card))}" alt=""><div><b>${escapeHTML(card.nome)}</b><small>${escapeHTML(card.raridade)} · ${escapeHTML(card.tipo)} · custo ${number(card.custo)}</small></div><button type="button" data-add-deck="${escapeHTML(card.id)}" ${chosen.length >= 5 ? 'disabled' : ''}>Adicionar</button></article>`).join('') || '<div class="empty-state">Nenhuma carta disponível para esse filtro.</div>';
}

document.addEventListener('click', (event) => {
  const add = event.target.closest('[data-add-deck]');
  const remove = event.target.closest('[data-remove-deck]');
  if (add && selectedDeck.length < 5) { selectedDeck.push(add.dataset.addDeck); renderDeck(); }
  if (remove) { selectedDeck = selectedDeck.filter(id => id !== remove.dataset.removeDeck); renderDeck(); }
});
$('#deck-search').addEventListener('input', renderDeck);
$('#clear-deck').addEventListener('click', () => { selectedDeck = []; renderDeck(); });
$('#save-deck').addEventListener('click', async () => {
  const button = $('#save-deck');
  button.disabled = true; button.textContent = 'Salvando...';
  try {
    const response = await fetch('/api/deck', { method: 'POST', credentials: 'same-origin', headers: {'Content-Type':'application/json'}, body: JSON.stringify({card_ids: selectedDeck}) });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || 'Não foi possível salvar o deck.');
    savedDeck = data.deck || [];
    selectedDeck = savedDeck.map(card => card.id);
    $('#deck-status').textContent = 'Deck salvo no banco compartilhado. Ele já está disponível para os duelos do Discord.';
    showNotice('Deck sincronizado com o SoulsBot e com o Discord.', 'success');
    renderDeck();
  } catch (error) { $('#deck-status').textContent = error.message; }
  finally { button.textContent = 'Salvar deck no SoulsBot'; renderDeck(); }
});


async function loadPlayers() {
  if (!currentUser) return;
  try {
    await fetch('/api/presence/heartbeat', {method:'POST', credentials:'same-origin'});
    const response = await fetch('/api/players', {credentials:'same-origin', cache:'no-store'});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Não foi possível carregar jogadores.');
    const players = (data.players || []).filter(player => !player.is_self);
    $('#challenge-player').innerHTML = '<option value="">Selecione um jogador</option>' + players.map(player => {
      const status = player.web_online ? ' · no site' : ` · Discord: ${player.discord_presence}`;
      return `<option value="${escapeHTML(player.id)}">${escapeHTML(player.name)}${escapeHTML(status)}</option>`;
    }).join('');
    $('#players-presence').textContent = players.length ? players.map(player => `${player.name}: ${player.web_online ? 'site online' : `Discord ${player.discord_presence}`}`).join(' · ') : 'Nenhum outro jogador disponível no servidor.';
  } catch (error) {
    $('#players-presence').textContent = error.message;
  }
}

async function sendChallenge() {
  const opponent_id = $('#challenge-player').value;
  const aposta = Number($('#challenge-bet').value);
  const button = $('#send-challenge');
  if (!opponent_id) return showNotice('Selecione um jogador para desafiar.', 'error');
  if (!Number.isInteger(aposta) || aposta < 0 || aposta > 500) return showNotice('A aposta deve ser um número inteiro entre 0 e 500.', 'error');
  button.disabled = true; button.textContent = 'Enviando...';
  try {
    const response = await fetch('/api/duels', {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'}, body:JSON.stringify({opponent_id, aposta})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Não foi possível criar o convite.');
    showNotice(`Convite #${data.duel_id} publicado no Discord.`, 'success');
    if (data.discord_message) window.open(data.discord_message, '_blank', 'noopener');
    await loadDuels();
  } catch (error) { showNotice(error.message, 'error'); }
  finally { button.disabled = false; button.textContent = 'Enviar convite'; }
}

async function loadDuels() {
  const list = $('#duel-list');
  if (!currentUser) { list.innerHTML = '<div class="empty-state">Entre com Discord para consultar seus duelos.</div>'; return; }
  list.innerHTML = '<div class="empty-state">Sincronizando duelos...</div>';
  try {
    const response = await fetch('/api/duels', {credentials:'same-origin', cache:'no-store'});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Não foi possível carregar os duelos.');
    const duels = data.duels || [];
    list.innerHTML = duels.length ? duels.map(duel => `<article class="duel-item"><div><small class="eyebrow">DUELO #${number(duel.id)}</small><h3>${duel.is_creator ? 'Você desafiou um jogador' : 'Você recebeu um convite'}</h3><p>${escapeHTML(duel.status)} · Rodada ${number(duel.current_round)}/5 · Aposta ${number(duel.aposta)} Denários por jogador</p></div><button class="primary" data-open-duel="${duel.id}">${duel.status === 'invited' && !duel.is_creator ? 'Aceitar convite' : 'Abrir partida'}</button></article>`).join('') : '<div class="empty-state">Você ainda não tem convites ou partidas registrados.</div>';
  } catch (error) { list.innerHTML = `<div class="empty-state">${escapeHTML(error.message)}</div>`; }
}

function connectDuelLive(duelId) {
  if (duelSocket) { try { duelSocket.close(); } catch (_) {} duelSocket = null; }
  if (duelRefreshHandle) { clearInterval(duelRefreshHandle); duelRefreshHandle = null; }
  const scheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  duelSocket = new WebSocket(`${scheme}//${window.location.host}/ws/duels/${encodeURIComponent(duelId)}`);
  duelSocket.addEventListener('message', (event) => {
    try {
      const payload = JSON.parse(event.data);
      if (payload.duel_id === Number(currentDuelId) && payload.type !== 'connected') refreshCurrentDuel();
    } catch (_) {}
  });
  // Fallback para redes/proxies que não mantenham WebSocket aberto.
  duelRefreshHandle = window.setInterval(() => refreshCurrentDuel(), 10000);
}

async function refreshCurrentDuel() {
  if (!currentDuelId || $('#duel-room').hidden) return;
  try {
    const response = await fetch(`/api/duels/${currentDuelId}`, {credentials:'same-origin', cache:'no-store'});
    const data = await response.json();
    if (response.ok) renderDuel(data);
  } catch (_) { /* A próxima tentativa automática fará a recuperação. */ }
}

async function openDuel(duelId) {
  currentDuelId = Number(duelId);
  connectDuelLive(currentDuelId);
  showPage('duels');
  const room = $('#duel-room');
  room.hidden = false;
  room.innerHTML = '<div class="empty-state">Carregando arena...</div>';
  try {
    let response = await fetch(`/api/duels/${currentDuelId}`, {credentials:'same-origin', cache:'no-store'});
    let data = await response.json();
    if (!response.ok && data.error === 'Duelo não encontrado.') throw new Error(data.error);
    if (!response.ok) {
      const accept = await fetch(`/api/duels/${currentDuelId}/accept`, {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'}, body:'{}'});
      const accepted = await accept.json();
      if (!accept.ok) throw new Error(accepted.error || 'Não foi possível aceitar o convite.');
      response = await fetch(`/api/duels/${currentDuelId}`, {credentials:'same-origin', cache:'no-store'});
      data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Não foi possível abrir a partida.');
      showNotice('Convite aceito. As apostas foram travadas e a partida começou.', 'success');
    }
    renderDuel(data);
  } catch (error) { room.innerHTML = `<div class="empty-state">${escapeHTML(error.message)}</div>`; }
}

function renderDuel(data) {
  const room = $('#duel-room');
  const duel = data.duel;
  const score = data.score || {};
  const isInvite = duel.status === 'invited';
  const cards = data.available_cards || [];
  const rounds = data.rounds || [];
  room.hidden = false;
  room.innerHTML = `<div class="section-head"><div><small class="eyebrow">ARENA · DUELO #${number(duel.id)}</small><h2>${duel.status === 'active' ? `Rodada ${duel.current_round}/5` : escapeHTML(duel.status)}</h2></div><button class="text-btn" id="close-duel">Voltar aos duelos</button></div>
    <div class="duel-score"><b>${number(score.creator || 0)} : ${number(score.opponent || 0)}</b><span>${number(score.rounds_played || 0)} rodada(s) concluída(s) · ${number(score.choices_received || 0)}/2 escolhas na rodada atual</span></div>
    ${isInvite ? (duel.is_creator ? `<p>Convite enviado. Aguardando o outro jogador aceitar. Aposta: <b>${number(duel.aposta)} Denários</b> por jogador.</p>` : `<p>Você recebeu um convite. Aposta: <b>${number(duel.aposta)} Denários</b> por jogador.</p><button class="primary" id="accept-duel">Aceitar duelo</button>`) : ''}
    ${duel.status === 'active' ? (score.own_choice_submitted ? '<div class="notice">Sua escolha foi registrada. Aguardando o adversário.</div>' : `<p>Escolha uma carta ainda não utilizada. Sua escolha fica oculta até o adversário confirmar.</p><div class="duel-cards">${cards.map(card => `<button class="duel-card" data-play-card="${escapeHTML(card.id)}"><img src="${escapeHTML(card.image_url || `/api/cards/${encodeURIComponent(card.id)}/image`)}" alt=""><b>${escapeHTML(card.nome)}</b><span>${number(card.poder)} poder · ${escapeHTML(card.tipo)}</span></button>`).join('')}</div>`) : ''}
    ${duel.status === 'finished' ? `<div class="notice success">Partida encerrada. ${duel.winner_id ? `Vencedor: ${duel.winner_id}. Prêmio: ${number(duel.payout)} Denários.` : 'Empate.'}</div>` : ''}
    <div class="duel-rounds">${rounds.map(round => `<article><b>Rodada ${number(round.round_no)}</b><span>${escapeHTML(round.card_a_name)} (${number(round.power_a)}) × ${escapeHTML(round.card_b_name)} (${number(round.power_b)})</span><small>${escapeHTML(round.narration || '')}</small></article>`).join('')}</div>`;
  $('#close-duel').addEventListener('click', () => { room.hidden = true; currentDuelId = null; if (duelSocket) duelSocket.close(); duelSocket = null; if (duelRefreshHandle) clearInterval(duelRefreshHandle); duelRefreshHandle = null; loadDuels(); });
  $('#accept-duel')?.addEventListener('click', async () => {
    const response = await fetch(`/api/duels/${duel.id}/accept`, {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'}, body:'{}'});
    const result = await response.json();
    if (!response.ok) { showNotice(result.error || 'Não foi possível aceitar.', 'error'); return; }
    await openDuel(duel.id);
  });
  room.querySelectorAll('[data-play-card]').forEach(button => button.addEventListener('click', async () => {
    room.querySelectorAll('[data-play-card]').forEach(item => item.disabled = true);
    const response = await fetch(`/api/duels/${duel.id}/moves`, {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'}, body:JSON.stringify({card_id:button.dataset.playCard})});
    const result = await response.json();
    if (!response.ok) { showNotice(result.error || 'Jogada não registrada.', 'error'); }
    else showNotice(result.status === 'waiting_opponent' ? 'Carta registrada. Aguardando o adversário.' : 'Rodada resolvida.', 'success');
    await openDuel(duel.id);
  }));
}

$('#refresh-duels')?.addEventListener('click', loadDuels);
$('#send-challenge')?.addEventListener('click', sendChallenge);
document.addEventListener('click', event => {
  const button = event.target.closest('[data-open-duel]');
  if (button) openDuel(button.dataset.openDuel);
});

function openCard(card) {
  $('#modal-image').src = imageUrl(card);
  $('#modal-image').alt = card.nome;
  $('#modal-rarity').textContent = text(card.raridade);
  $('#modal-title').textContent = text(card.nome);
  $('#modal-description').textContent = text(card.descricao, 'Esta carta não possui descrição adicional.');
  $('#modal-category').textContent = text(card.categoria);
  $('#modal-type').textContent = text(card.tipo);
  $('#modal-power').textContent = text(card.poder);
  $('#modal-cost').textContent = text(card.custo);
  $('#modal-quantity').textContent = text(card.quantidade);
  $('#modal-skill').textContent = text(card.habilidade);
  $('#card-modal').hidden = false;
}

document.addEventListener('click', (event) => {
  const button = event.target.closest('[data-card-id]');
  if (button) {
    const card = collection.find((item) => item.id === button.dataset.cardId);
    if (card) openCard(card);
  }
});
$('#modal-close').addEventListener('click', () => { $('#card-modal').hidden = true; });
$('#card-modal').addEventListener('click', (event) => { if (event.target === $('#card-modal')) $('#card-modal').hidden = true; });
document.addEventListener('keydown', (event) => { if (event.key === 'Escape') $('#card-modal').hidden = true; });
['search', 'rarity', 'category', 'type'].forEach((id) => $(`#${id}`).addEventListener('input', renderCollection));
$('#login-button').addEventListener('click', () => { const next = window.location.pathname + window.location.search; window.location.href = `/auth/discord/login?next=${encodeURIComponent(next)}`; });
$('#logout-button').addEventListener('click', async () => {
  await fetch('/auth/logout', { method: 'POST', credentials: 'same-origin' });
  collection = [];
  $('#collection-grid').innerHTML = '<div class="empty-state">Entre com Discord para carregar as cartas.</div>';
  $('#featured').innerHTML = '';
  $('#souls').textContent = $('#denarios').textContent = '—';
  showPage('home');
  await loadAccount();
});

loadAccount().then(() => { if (currentUser) { loadPlayers(); window.setInterval(loadPlayers, 30000); } const requested = new URLSearchParams(window.location.search).get('duel'); if (requested && currentUser && /^\d+$/.test(requested)) openDuel(requested); });
