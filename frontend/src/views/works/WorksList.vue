<template>
  <main class="works-list-shell" data-testid="works-list-shell">
    <header class="works-list-header">
      <p class="eyebrow">Workbench</p>
      <h1>Bookshelf</h1>
      <p class="description">Stage 0 page shell. Work list behavior is implemented in later stages.</p>
    </header>

    <section class="works-list-placeholder" aria-label="works placeholder">
      <div class="placeholder-card">WorksList Shell</div>
    </section>
  </main>
</template>

<style scoped>
.works-list-shell {
  min-height: 100vh;
  padding: 32px;
  background: #f8fafc;
  color: #111827;
}

.works-list-header {
  max-width: 720px;
}

.eyebrow {
  margin: 0 0 8px;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.works-list-header h1 {
  margin: 0;
  font-size: 32px;
}

.description {
  margin: 12px 0 0;
  color: #475569;
}

.works-list-placeholder {
  margin-top: 24px;
}

.placeholder-card {
  display: grid;
  min-height: 180px;
  place-items: center;
  border: 1px dashed #cbd5e1;
  border-radius: 20px;
  background: #ffffff;
  color: #64748b;
  font-weight: 700;
}
</style>
