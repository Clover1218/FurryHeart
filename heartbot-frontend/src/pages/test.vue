<template>
  <div class="layout">
    <!-- 左侧图谱 -->
    <div class="graph-wrapper">
      <div ref="graphRef" class="graph-container"></div>
    </div>

    <!-- 右侧固定信息栏 -->
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
import { onMounted, ref } from 'vue'

const graphRef = ref<HTMLDivElement>()

const selectedNode = ref<any>(null)

let graph: Graph | null = null

/**
 * 原始数据
 */
const rawGraphData = {
  nodes: [
    {
      id: '635b086c-726d-4585-afc2-30a7b2133bda',
      label: '情绪上头',
      type: 'entity',

      memories: [
        {
          id: '1',

          content: '用户推测老师情绪容易上头是因为更年期。',

          emotion: 'neutral',

          importance: 0.4,
        },
      ],
    },

    {
      id: '8942ed75-9f1d-4640-bf49-67ca124f9480',
      label: '老师',
      type: 'entity',

      memories: [
        {
          id: '2',

          content: '老师在群里压力商业运营和硬件端的同学。',

          emotion: 'fear',

          importance: 0.75,
        },
      ],
    },

    {
      id: 'ff62607c-95a0-40dc-bfb0-00a1c1454881',
      label: '用户',
      type: 'entity',

      memories: [
        {
          id: '3',

          content: '用户喜欢晒太阳，享受安静放松的时光。',

          emotion: 'joy',

          importance: 0.5,
        },
      ],
    },

    {
      id: 'd58f8850-9e7f-4af5-803f-c48c7bcca807',
      label: 'AI情感陪伴项目',
      type: 'entity',

      memories: [
        {
          id: '4',

          content: '用户参与了一个AI情感陪伴项目。',

          emotion: 'neutral',

          importance: 0.7,
        },
      ],
    },

    {
      id: '9dfe08cf-726c-42ba-a5fa-d12a90711b69',
      label: '红烧肉盖浇饭',
      type: 'entity',

      memories: [
        {
          id: '5',

          content: '用户喜欢吃红烧肉盖浇饭。',

          emotion: 'joy',

          importance: 0.6,
        },
      ],
    },
  ],

  edges: [
    {
      source: '8942ed75-9f1d-4640-bf49-67ca124f9480',

      target: '635b086c-726d-4585-afc2-30a7b2133bda',

      relation: '容易',
    },

    {
      source: 'ff62607c-95a0-40dc-bfb0-00a1c1454881',

      target: 'd58f8850-9e7f-4af5-803f-c48c7bcca807',

      relation: '参与',
    },

    {
      source: 'ff62607c-95a0-40dc-bfb0-00a1c1454881',

      target: '9dfe08cf-726c-42ba-a5fa-d12a90711b69',

      relation: '喜欢',
    },
  ],
}

/**
 * 关键：
 * 预处理 label
 * 不使用 callback
 */
const graphData = {
  nodes: rawGraphData.nodes.map((node) => ({
    ...node,

    style: {
      labelText:
        node.label.length > 8
          ? node.label.slice(0, 8) + '...'
          : node.label,
    },
  })),

  edges: rawGraphData.edges.map((edge, index) => ({
    ...edge,

    id: `edge-${index}`,

    style: {
      labelText: edge.relation,
    },
  })),
}

/**
 * node map
 */
const nodeMap = new Map()

graphData.nodes.forEach((node) => {
  nodeMap.set(node.id, node)
})

onMounted(async () => {
  if (!graphRef.value) return

  graph = new Graph({
    container: graphRef.value,

    width: graphRef.value.clientWidth,

    height: graphRef.value.clientHeight,

    autoFit: 'view',

    data: graphData,

    layout: {
      type: 'fruchterman',

      gravity: 8,

      speed: 5,

      clustering: true,
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

        labelFill: '#cbd5e1',

        labelAutoRotate: false,

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

  setTimeout(() => {
    graph?.fitView()
  }, 300)

  /**
   * 默认节点
   */
  selectedNode.value = graphData.nodes[0]

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

    // graphData.nodes.forEach((node) => {
    //   graph?.setElementState(node.id, {
    //     selected: false,
    //   })
    // })

    // graph?.setElementState(nodeId, {
    //   selected: true,
    // })
  })
})
</script>

<style scoped>
.layout {
  width: 100%;

  height: 100vh;

  display: flex;

  background: #020617;
}

/* 左侧图谱 */

.graph-wrapper {
  flex: 1;

  position: relative;
}

.graph-container {
  width: 100%;

  height: 100%;
}

/* 右侧栏 */

.sidebar {
  width: 360px;

  background: #0f172a;

  border-left: 1px solid rgba(255,255,255,0.08);

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
  background: rgba(255,255,255,0.04);

  border: 1px solid rgba(255,255,255,0.06);

  border-radius: 16px;

  padding: 16px;

  transition: all 0.2s;
}

.memory-card:hover {
  background: rgba(255,255,255,0.06);

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