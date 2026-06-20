<script setup lang="ts">
import { ElContainer, ElHeader, ElMain } from 'element-plus'
import TopNav from '@/components/layout/TopNav.vue'

const cachedViews = ['VideoLibraryPage', 'WeeksPage', 'CreatorsPage', 'HomePage']
</script>

<template>
  <el-container class="h-screen">
    <el-header height="56px" class="!p-0">
      <TopNav />
    </el-header>
    <el-main class="!p-0">
      <router-view v-slot="{ Component }">
        <keep-alive :max="5" :include="cachedViews">
          <component :is="Component" />
        </keep-alive>
      </router-view>
    </el-main>
  </el-container>
</template>
