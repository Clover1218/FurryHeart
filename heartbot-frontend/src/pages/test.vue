<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
// @ts-ignore
import * as THREE from 'three'

const el = ref<HTMLDivElement | null>(null)

let renderer: THREE.WebGLRenderer
let scene: THREE.Scene
let camera: THREE.PerspectiveCamera
let frameId: number

let water: THREE.Mesh
let light: THREE.DirectionalLight

let time = 0

onMounted(() => {
  init()
  animate()
})

onBeforeUnmount(() => {
  cancelAnimationFrame(frameId)
  renderer.dispose()
})

function init() {
  const width = el.value!.clientWidth
  const height = el.value!.clientHeight

  // 🎬 renderer
  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(width, height)
  renderer.shadowMap.enabled = true
  el.value!.appendChild(renderer.domElement)

  // 🌍 scene
  scene = new THREE.Scene()

  // 📷 camera
  camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 100)
  camera.position.set(0, 2, 5)

  // ☀️ 主光（太阳）
  light = new THREE.DirectionalLight(0xffffff, 1)
  light.position.set(5, 5, 5)
  light.castShadow = true
  scene.add(light)

  // 🌫️ 环境光
  scene.add(new THREE.AmbientLight(0xffffff, 0.3))

  // 🌊 水面
  const geo = new THREE.PlaneGeometry(10, 10, 128, 128)
  const mat = new THREE.MeshStandardMaterial({
    color: 0x3399ff,
    metalness: 0.7,
    roughness: 0.2
  })

  water = new THREE.Mesh(geo, mat)
  water.rotation.x = -Math.PI / 2
  water.receiveShadow = true
  scene.add(water)

  // 🪑 一个“桌子”（盒子）
  const box = new THREE.Mesh(
    new THREE.BoxGeometry(0.8, 0.5, 0.8),
    new THREE.MeshStandardMaterial({ color: 0xffffff })
  )
  box.position.y = 0.25
  box.castShadow = true
  scene.add(box)

  // 🟫 地面（接阴影）
  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(20, 20),
    new THREE.MeshStandardMaterial({ color: 0xdddddd })
  )
  ground.rotation.x = -Math.PI / 2
  ground.position.y = -0.01
  ground.receiveShadow = true
  scene.add(ground)

  window.addEventListener('resize', onResize)
}

function onResize() {
  const width = el.value!.clientWidth
  const height = el.value!.clientHeight

  camera.aspect = width / height
  camera.updateProjectionMatrix()
  renderer.setSize(width, height)
}

function animate() {
  frameId = requestAnimationFrame(animate)
  time += 0.01

  // 🌊 水面波动
  const pos = water.geometry.attributes.position
  for (let i = 0; i < pos.count; i++) {
    pos.setY(i, Math.sin(i * 0.1 + time) * 0.1)
  }
  pos.needsUpdate = true

  // ☀️ 太阳移动（时间流动）
  light.position.x = Math.sin(time) * 5
  light.position.y = 3 + Math.cos(time) * 2

  // 🌅 天空颜色变化
  const t = (Math.sin(time * 0.2) + 1) / 2
  scene.background = new THREE.Color().setHSL(
    0.6 - t * 0.5, // 蓝 → 橙
    0.5,
    0.3 + t * 0.4
  )

  renderer.render(scene, camera)
}
</script>

<template>
  <div class="three-container" ref="el"></div>
</template>

<style scoped>
.three-container {
  width: 100%;
  height: 100vh;
  background: #000;
}
</style>