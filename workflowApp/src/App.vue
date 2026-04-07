<script setup lang="ts">
import { ref } from 'vue'
import WorkflowBuilder from './views/WorkflowBuilder.vue'
import Chat from './views/Chat.vue'
import CodeEditor from './views/CodeEditor.vue'

type TabId = 'workflow' | 'chat' | 'editor'

const activeTab = ref<TabId>('workflow')

const tabs: { id: TabId; label: string }[] = [
  { id: 'workflow', label: 'Workflow Builder' },
  { id: 'chat', label: 'Chat' },
  { id: 'editor', label: 'Code Editor' },
]
</script>

<template>
  <div class="flex flex-col h-screen">
    <!-- Tab Navigation -->
    <nav class="flex bg-[var(--color-surface)] border-b border-[var(--color-border)]">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        @click="activeTab = tab.id"
        class="px-6 py-3 text-sm font-medium transition-colors relative"
        :class="[
          activeTab === tab.id
            ? 'text-[var(--color-primary)]'
            : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)]'
        ]"
      >
        {{ tab.label }}
        <span
          v-if="activeTab === tab.id"
          class="absolute bottom-0 left-0 right-0 h-0.5 bg-[var(--color-primary)]"
        />
      </button>
    </nav>

    <!-- Tab Content -->
    <main class="flex-1 overflow-hidden">
      <WorkflowBuilder v-if="activeTab === 'workflow'" />
      <Chat v-if="activeTab === 'chat'" />
      <CodeEditor v-if="activeTab === 'editor'" />
    </main>
  </div>
</template>
