<template>
  <div class="memory-graph-container">
    <!-- 左侧图谱 -->
    <div class="graph-wrapper">
      <div ref="graphRef" class="graph-container"></div>
    </div>

    <!-- 右侧信息栏 -->
    <div class="sidebar">
      <template v-if="selectedNode">
        <div class="title">
          {{ selectedNode.label }}
        </div>

        <div class="type">
          {{ selectedNode.type }}
        </div>

        <div class="section-title">
          关联记忆
        </div>

        <div class="memory-list">
          <div
            v-for="memory in selectedNode.memories"
            :key="memory.id"
            class="memory-card"
          >
            <div class="memory-content">
              {{ memory.content }}
            </div>

            <div class="memory-footer">
              <span>{{ memory.emotion }}</span>

              <span>
                importance {{ memory.importance }}
              </span>
            </div>
          </div>
        </div>
      </template>

      <template v-else>
        <div class="empty">
          点击左侧节点查看记忆
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Graph } from '@antv/g6'
import {
  onMounted,
  onUnmounted,
  ref,
  watch,
  nextTick,
} from 'vue'

const props = defineProps<{
  graphData: {
    nodes: any[]
    edges: any[]
  }
}>()

const graphRef = ref<HTMLDivElement>()

const selectedNode = ref<any>(null)

let graph: Graph | null = null

/**
 * 处理后的数据
 */
const processedData = ref({
  nodes: [] as any[],
  edges: [] as any[],
})

/**
 * node map
 */
const nodeMap = new Map()

/**
 * 数据预处理
 */
const processData = () => {
  if (!props.graphData) return

  processedData.value = {
    nodes:
      props.graphData.nodes?.map((node) => ({
        ...node,

        style: {
          labelText:
            node.label?.length > 8
              ? node.label.slice(0, 8) + '...'
              : node.label,
        },
      })) || [],

    edges:
      props.graphData.edges?.map((edge, index) => ({
        ...edge,

        id: edge.id || `edge-${index}`,

        style: {
          labelText: edge.relation || '',
        },
      })) || [],
  }

  nodeMap.clear()

  processedData.value.nodes.forEach((node) => {
    nodeMap.set(node.id, node)
  })
}

/**
 * 初始化图谱
 */
const initGraph = async () => {
  await nextTick()

  if (!graphRef.value) return

  if (processedData.value.nodes.length === 0) return

  /**
   * 销毁旧实例
   */
  if (graph) {
    graph.destroy()
    graph = null
  }

  graph = new Graph({
    container: graphRef.value,

    /**
     * 关键：
     * 不要用 clientWidth/clientHeight
     */
    width: graphRef.value.offsetWidth || 800,

    height: graphRef.value.offsetHeight || 600,

    autoFit: 'view',

    data: processedData.value,

    layout: {
      type: 'force-atlas2',
        
      preventOverlap: true,
        
      kr: 120,
        
      kg: 20,
        
      nodeSize: 46,
        
      maxIteration: 2000,
    },

    node: {
      type: 'circle',

      style: {
        size: 46,

        fill: '#1e293b',

        stroke: '#64748b',

        lineWidth: 2,

        labelFill: '#ffffff',

        labelFontSize: 11,

        cursor: 'pointer',
      },

      state: {
        selected: {
          stroke: '#60a5fa',

          shadowBlur: 20,

          shadowColor: '#60a5fa',
        },
      },
    },

    edge: {
      type: 'line',

      style: {
        stroke: '#64748b',

        lineWidth: 1.5,

        endArrow: false,

        /**
         * 保持水平
         */
        labelAutoRotate: false,

        labelFill: '#cbd5e1',

        labelFontSize: 10,

        labelBackground: true,

        labelBackgroundFill: '#020617',

        labelPadding: [2, 6],

        labelRadius: 4,
      },
    },

    behaviors: [
      'drag-canvas',
      'zoom-canvas',
      'drag-element',
    ],
  })

  await graph.render()

  /**
   * force layout 必须延迟 fit
   */
  setTimeout(() => {
    graph?.fitView()
  }, 500)

  /**
   * 默认选中第一个节点
   */
  if (processedData.value.nodes.length > 0) {
    selectedNode.value =
      processedData.value.nodes[0]

    graph.setElementState(
      processedData.value.nodes[0].id,
      ['selected']
    )
  }

  /**
   * 点击节点
   */
  graph.on('node:click', (evt: any) => {
    const nodeId =
      evt.target?.id ||
      evt.target?.config?.id

    if (!nodeId) return

    const nodeData = nodeMap.get(nodeId)

    if (!nodeData) return

    selectedNode.value = nodeData

    /**
     * 清空状态
     */
    processedData.value.nodes.forEach((node) => {
      graph?.setElementState(node.id, [])
    })

    /**
     * 高亮
     */
    graph?.setElementState(nodeId, 
      ['selected'],
    )
  })
}

/**
 * resize
 */
const handleResize = () => {
  if (!graph || !graphRef.value) return

  graph.setSize(
    graphRef.value.offsetWidth || 800,
    graphRef.value.offsetHeight || 600
  )

  setTimeout(() => {
    graph?.fitView()
  }, 300)
}

/**
 * watch 数据
 */
watch(
  () => props.graphData,
  async () => {
    processData()

    await initGraph()
  },
  {
    immediate: true,

    deep: true,
  }
)

onMounted(() => {
  window.addEventListener(
    'resize',
    handleResize
  )
})

onUnmounted(() => {
  window.removeEventListener(
    'resize',
    handleResize
  )

  if (graph) {
    graph.destroy()
  }
})
</script>

<style scoped>
.memory-graph-container {
  width: 100%;

  height: 100vh;

  display: flex;

  overflow: hidden;

  background: #020617;
}

/**
 * 左侧图谱
 */
.graph-wrapper {
  flex: 1;

  min-width: 0;

  min-height: 0;

  position: relative;
}

.graph-container {
  width: 100%;

  height: 100%;
}

/**
 * 右侧栏
 */
.sidebar {
  width: 360px;

  flex-shrink: 0;

  background: #0f172a;

  border-left: 1px solid
    rgba(255, 255, 255, 0.08);

  padding: 24px;

  overflow-y: auto;
}

.title {
  font-size: 30px;

  color: white;

  font-weight: 700;
}

.type {
  margin-top: 8px;

  color: #94a3b8;

  font-size: 13px;

  text-transform: uppercase;
}

.section-title {
  margin-top: 28px;

  margin-bottom: 16px;

  color: #e2e8f0;

  font-size: 15px;

  font-weight: 600;
}

.memory-list {
  display: flex;

  flex-direction: column;

  gap: 14px;
}

.memory-card {
  background: rgba(255, 255, 255, 0.04);

  border: 1px solid
    rgba(255, 255, 255, 0.06);

  border-radius: 16px;

  padding: 16px;

  transition: all 0.2s;
}

.memory-card:hover {
  background: rgba(255, 255, 255, 0.06);

  transform: translateY(-2px);
}

.memory-content {
  color: #f8fafc;

  line-height: 1.7;

  font-size: 14px;
}

.memory-footer {
  margin-top: 12px;

  display: flex;

  justify-content: space-between;

  color: #94a3b8;

  font-size: 12px;
}

.empty {
  color: #94a3b8;

  margin-top: 40px;
}
</style>