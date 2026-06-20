<template>
  <section class="bg-gradient-to-br from-[#CCF0FC] via-[#E6F7FD] to-bg rounded-[16px]
                  py-24 px-16 text-center mt-6 shadow-[var(--shadow-default)]">
    <h1 class="text-[2.5rem] font-bold tracking-[-0.02em] text-text mb-4">
      发现每周好内容
    </h1>
    <p class="text-lg text-[#4B7A8F] max-w-[480px] mx-auto mb-9 leading-relaxed">
      基于B站「每周必看」数据，发现优质创作者、热门品类与内容趋势
    </p>
    <router-link
      to="/videos"
      class="inline-block px-7 py-2.5 bg-blue text-white no-underline
             rounded-[12px] font-medium transition-colors duration-200
             hover:bg-[#0099D6]"
    >
      浏览视频库
    </router-link>
  </section>
</template>
