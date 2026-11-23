const $ = (selector) => document.querySelector(selector);
let collection = [];
let currentUser = null;
let savedDeck = [];
let selectedDeck = [];

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
  $('#page-title').textContent = page === 'collection' ? 'Minha coleção' : page === 'deck' ? 'Meu deck' : 'Visão geral';
  if (page === 'deck') loadDeck();
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
$('#login-button').addEventListener('click', () => { window.location.href = '/auth/discord/login'; });
$('#logout-button').addEventListener('click', async () => {
  await fetch('/auth/logout', { method: 'POST', credentials: 'same-origin' });
  collection = [];
  $('#collection-grid').innerHTML = '<div class="empty-state">Entre com Discord para carregar as cartas.</div>';
  $('#featured').innerHTML = '';
  $('#souls').textContent = $('#denarios').textContent = '—';
  showPage('home');
  await loadAccount();
});

loadAccount();
