<script setup lang="ts">
defineProps<{
  label?: string
}>()
</script>

<template>
  <div class="al-root">
    <div class="al-body">
      <div class="al-scanner-box">
        <div class="al-beam" />
        <div class="al-grid" />
        <div class="al-ghost-bars">
          <div class="al-bar" style="height:28px" />
          <div class="al-bar" style="height:56px" />
          <div class="al-bar" style="height:18px" />
          <div class="al-bar" style="height:72px" />
          <div class="al-bar" style="height:44px" />
          <div class="al-bar" style="height:64px" />
          <div class="al-bar" style="height:10px" />
        </div>
      </div>

      <div class="al-label-row">
        <span class="al-label-text">{{ label ?? '分析中…' }}</span>
        <div class="al-dots">
          <span class="al-dot" style="--dot-delay: 0s" />
          <span class="al-dot" style="--dot-delay: 0.25s" />
          <span class="al-dot" style="--dot-delay: 0.5s" />
        </div>
      </div>

      <div class="w-full max-w-[360px] space-y-3">
        <el-skeleton :rows="1" animated />
        <el-skeleton :rows="1" animated />
        <el-skeleton :rows="1" animated />
      </div>
    </div>
  </div>
</template>

<style scoped>
.al-root {
  position: relative;
  width: 100%;
  overflow: hidden;
  border-radius: 16px;
  border: 1px solid var(--color-border, #E5E7EB);
  background: linear-gradient(180deg, #FAFBFC 0%, #F4F6F8 100%);
  user-select: none;
}

.al-body {
  padding: 20px 24px;
  min-height: 200px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
}

.al-scanner-box {
  position: relative;
  width: 100%;
  max-width: 360px;
  height: 128px;
  margin: 0 auto;
  overflow: hidden;
  border-radius: 8px;
  background: linear-gradient(180deg, #F0F2F5 0%, #E8EBEF 100%);
}

.al-beam {
  position: absolute;
  left: 0;
  width: 100%;
  height: 1.5px;
  pointer-events: none;
  background: linear-gradient(90deg,
    transparent 0%,
    rgba(0,174,236,0.15) 15%,
    rgba(0,174,236,0.55) 35%,
    rgba(0,174,236,0.8) 50%,
    rgba(0,174,236,0.55) 65%,
    rgba(0,174,236,0.15) 85%,
    transparent 100%
  );
  box-shadow: 0 0 12px rgba(0,174,236,0.25), 0 0 2px rgba(0,174,236,0.4);
  animation: al-sweep 2.8s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}

.al-grid {
  position: absolute;
  inset: 0;
  opacity: 0.04;
  pointer-events: none;
  background-image:
    repeating-linear-gradient(0deg, transparent, transparent 19px, #000 19px, #000 20px),
    repeating-linear-gradient(90deg, transparent, transparent 39px, #000 39px, #000 40px);
}

.al-ghost-bars {
  position: absolute;
  bottom: 16px;
  left: 24px;
  right: 24px;
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  gap: 12px;
  opacity: 0.12;
}

.al-bar {
  width: 20px;
  border-radius: 2px 2px 0 0;
  background: #00AEEC;
}

.al-label-row {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.al-label-text {
  font-size: 0.875rem;
  font-weight: 500;
  letter-spacing: 0.025em;
  color: #00AEEC;
  animation: al-breathe 2.8s ease-in-out infinite;
}

.al-dots {
  display: flex;
  align-items: center;
  gap: 4px;
}

.al-dot {
  display: inline-block;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #00AEEC;
  opacity: 0;
  animation: al-dot-pulse 1.6s ease-in-out infinite;
  animation-delay: var(--dot-delay, 0s);
}

@keyframes al-sweep {
  0%   { top: -2px; opacity: 0; }
  8%   { top: -2px; opacity: 1; }
  45%  { top: calc(100% + 2px); opacity: 1; }
  55%  { top: calc(100% + 2px); opacity: 0; }
  100% { top: calc(100% + 2px); opacity: 0; }
}

@keyframes al-breathe {
  0%, 100% { opacity: 0.5; }
  50%      { opacity: 1; }
}

@keyframes al-dot-pulse {
  0%, 100% { opacity: 0.15; }
  50%      { opacity: 0.8; }
}
</style>
