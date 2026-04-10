<template>
  <section class="page-hero">
    <div class="hero-copy">
      <div class="hero-eyebrow">{{ eyebrow }}</div>
      <h1>{{ title }}</h1>
      <p>{{ description }}</p>
    </div>
    <slot />
  </section>
</template>

<script setup>
defineProps({
  eyebrow: {
    type: String,
    required: true
  },
  title: {
    type: String,
    required: true
  },
  description: {
    type: String,
    required: true
  }
})
</script>

<style scoped>
.page-hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
  padding: 28px 32px;
  border-radius: 24px;
  background: linear-gradient(180deg, #F8FAFC 0%, #FFFFFF 100%);
  border: 1px solid #E5E7EB;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.04);
}

.hero-copy {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.hero-eyebrow {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #6366F1;
}

.page-hero h1 {
  margin: 0;
  font-size: 28px;
  line-height: 1.2;
  color: #111827;
}

.page-hero p {
  margin: 0;
  max-width: 760px;
  font-size: 14px;
  line-height: 1.7;
  color: #4B5563;
}
</style>
