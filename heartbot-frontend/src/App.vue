<script setup lang="ts">
import { NDialogProvider } from 'naive-ui'


</script>
<template>
  <n-dialog-provider>
    <router-view />
  </n-dialog-provider>
  
</template>

<style scoped>
:global(body), :global(html) {
  margin: 0;
  padding: 0;
  overflow: hidden;
  width: 100%;
  height: 100%;
}
</style>
