const $ = (selector) => document.querySelector(selector);
let collection = [];
let currentUser = null;

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
  $('#page-title').textContent = page === 'collection' ? 'Minha coleção' : 'Visão geral';
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
