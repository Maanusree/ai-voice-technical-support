/**
 * Knowledge Base Explorer Module
 */
class KnowledgeBaseExplorer {
  constructor() {
    this.articles = [];
    this.init();
  }

  async init() {
    await this.loadArticles();

    const searchInput = document.getElementById('kbSearchInput');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        this.filterArticles(query);
      });
    }
  }

  async loadArticles() {
    const grid = document.getElementById('kbCardsGrid');
    if (!grid) return;

    try {
      const resp = await fetch('/api/knowledge/articles');
      const data = await resp.json();
      this.articles = data.articles || [];
      this.renderArticles(this.articles);
    } catch (e) {
      console.error('Error fetching knowledge articles:', e);
    }
  }

  renderArticles(articles) {
    const grid = document.getElementById('kbCardsGrid');
    if (!grid) return;

    if (articles.length === 0) {
      grid.innerHTML = '<p style="color: var(--text-muted); grid-column: 1/-1;">No technical support articles matched your search.</p>';
      return;
    }

    grid.innerHTML = articles.map(art => `
      <div class="kb-card">
        <span class="badge info" style="margin-bottom: 0.5rem;">${art.category}</span>
        <h3>${art.title}</h3>
        <p style="font-size: 0.85rem; color: var(--text-secondary); margin: 0.4rem 0;">${art.summary}</p>
        
        <div style="margin-top: 0.75rem;">
          <strong style="font-size: 0.8rem; color: var(--text-primary);">Diagnostic Step Flow:</strong>
          <ol class="kb-steps-list">
            ${art.diagnostic_flow.map(s => `<li><strong>Step ${s.step_number}:</strong> ${s.instruction}</li>`).join('')}
          </ol>
        </div>

        ${art.faqs && art.faqs.length > 0 ? `
          <div style="margin-top: 0.75rem; padding-top: 0.5rem; border-top: 1px solid var(--border-color);">
            <strong style="font-size: 0.8rem; color: var(--accent-cyan);">Quick FAQ:</strong>
            <p style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 0.2rem;">
              <strong>Q:</strong> ${art.faqs[0].question}<br>
              <strong>A:</strong> ${art.faqs[0].answer}
            </p>
          </div>
        ` : ''}
      </div>
    `).join('');
  }

  filterArticles(query) {
    if (!query) {
      this.renderArticles(this.articles);
      return;
    }

    const filtered = this.articles.filter(art => {
      return (
        art.title.toLowerCase().includes(query) ||
        art.category.toLowerCase().includes(query) ||
        art.summary.toLowerCase().includes(query) ||
        art.keywords.some(k => k.toLowerCase().includes(query))
      );
    });

    this.renderArticles(filtered);
  }
}

window.KnowledgeBaseExplorer = KnowledgeBaseExplorer;
