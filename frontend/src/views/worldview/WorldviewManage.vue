<template>
  <div class="worldview-manage">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="力量体系" name="power">
        <el-card>
          <el-form :model="powerForm" label-width="100px">
            <el-form-item label="体系名称">
              <el-input v-model="powerForm.name" placeholder="如：修炼境界" />
            </el-form-item>
            <el-form-item label="等级列表">
              <div v-for="(level, index) in powerForm.levels" :key="index" style="margin-bottom: 10px;">
                <el-input v-model="powerForm.levels[index]" style="width: 200px;" />
                <el-button type="danger" size="small" @click="removeLevel(index)" style="margin-left: 10px;">删除</el-button>
              </div>
              <el-input v-model="newLevel" @keyup.enter="addLevel" placeholder="添加等级" style="width: 200px;" />
              <el-button type="primary" size="small" @click="addLevel" style="margin-left: 10px;">添加</el-button>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="savePowerSystem">保存</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>
      
      <el-tab-pane label="功法" name="techniques">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>功法列表</span>
              <el-button type="primary" size="small" @click="showTechniqueDialog">添加功法</el-button>
            </div>
          </template>
          
          <el-table :data="techniques">
            <el-table-column prop="name" label="名称" />
            <el-table-column prop="level" label="等级">
              <template #default="{ row }">
                {{ row.level?.name || '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" show-overflow-tooltip />
            <el-table-column prop="effect" label="效果" show-overflow-tooltip />
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button type="danger" size="small" @click="deleteTechnique(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
      
      <el-tab-pane label="势力" name="factions">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>势力列表</span>
              <el-button type="primary" size="small" @click="showFactionDialog">添加势力</el-button>
            </div>
          </template>
          
          <el-table :data="factions">
            <el-table-column prop="name" label="名称" />
            <el-table-column prop="level" label="等级" />
            <el-table-column prop="leader" label="领袖" />
            <el-table-column prop="territory" label="地盘" />
            <el-table-column prop="description" label="描述" show-overflow-tooltip />
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button type="danger" size="small" @click="deleteFaction(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
      
      <el-tab-pane label="地点" name="locations">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>地点列表</span>
              <el-button type="primary" size="small" @click="showLocationDialog">添加地点</el-button>
            </div>
          </template>
          
          <el-table :data="locations">
            <el-table-column prop="name" label="名称" />
            <el-table-column prop="description" label="描述" show-overflow-tooltip />
            <el-table-column prop="importance" label="重要度" />
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button type="danger" size="small" @click="deleteLocation(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
      
      <el-tab-pane label="物品" name="items">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>物品列表</span>
              <el-button type="primary" size="small" @click="showItemDialog">添加物品</el-button>
            </div>
          </template>
          
          <el-table :data="items">
            <el-table-column prop="name" label="名称" />
            <el-table-column prop="item_type" label="类型">
              <template #default="{ row }">
                <el-tag>{{ getItemTypeName(row.item_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="rarity" label="稀有度" />
            <el-table-column prop="effect" label="效果" show-overflow-tooltip />
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button type="danger" size="small" @click="deleteItem(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
      
      <el-tab-pane label="一致性检查" name="check">
        <el-card>
          <el-button type="primary" @click="checkConsistency" :loading="checking">检查一致性</el-button>
          
          <div v-if="issues.length > 0" style="margin-top: 20px;">
            <el-alert v-for="issue in issues" :key="issue.description" :title="issue.description" :type="issue.severity === 'error' ? 'error' : 'warning'" show-icon style="margin-bottom: 10px;">
              <template #default>
                <p>位置: {{ issue.location }}</p>
                <p>建议: {{ issue.suggestion }}</p>
              </template>
            </el-alert>
          </div>
          
          <el-empty v-else-if="!checking" description="暂无一致性问题" />
        </el-card>
      </el-tab-pane>
    </el-tabs>
    
    <el-dialog v-model="techniqueDialogVisible" title="添加功法" width="500px">
      <el-form :model="techniqueForm" label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="techniqueForm.name" />
        </el-form-item>
        <el-form-item label="等级">
          <el-input v-model="techniqueForm.level_name" placeholder="如：天阶" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="techniqueForm.description" type="textarea" />
        </el-form-item>
        <el-form-item label="效果">
          <el-input v-model="techniqueForm.effect" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="techniqueDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createTechnique">创建</el-button>
      </template>
    </el-dialog>
    
    <el-dialog v-model="factionDialogVisible" title="添加势力" width="500px">
      <el-form :model="factionForm" label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="factionForm.name" />
        </el-form-item>
        <el-form-item label="等级">
          <el-input v-model="factionForm.level" />
        </el-form-item>
        <el-form-item label="领袖">
          <el-input v-model="factionForm.leader" />
        </el-form-item>
        <el-form-item label="地盘">
          <el-input v-model="factionForm.territory" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="factionForm.description" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="factionDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createFaction">创建</el-button>
      </template>
    </el-dialog>
    
    <el-dialog v-model="locationDialogVisible" title="添加地点" width="500px">
      <el-form :model="locationForm" label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="locationForm.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="locationForm.description" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="locationDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createLocation">创建</el-button>
      </template>
    </el-dialog>
    
    <el-dialog v-model="itemDialogVisible" title="添加物品" width="500px">
      <el-form :model="itemForm" label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="itemForm.name" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="itemForm.item_type">
            <el-option label="法宝" value="artifact" />
            <el-option label="丹药" value="pill" />
            <el-option label="材料" value="material" />
            <el-option label="功法" value="scripture" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="稀有度">
          <el-input v-model="itemForm.rarity" />
        </el-form-item>
        <el-form-item label="效果">
          <el-input v-model="itemForm.effect" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="itemDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createItem">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api'

const route = useRoute()
const novelId = computed(() => route.params.id)

const activeTab = ref('power')
const powerForm = ref({ name: '', levels: [] })
const newLevel = ref('')
const techniques = ref([])
const factions = ref([])
const locations = ref([])
const items = ref([])
const issues = ref([])
const checking = ref(false)

const techniqueDialogVisible = ref(false)
const factionDialogVisible = ref(false)
const locationDialogVisible = ref(false)
const itemDialogVisible = ref(false)

const techniqueForm = ref({ name: '', level_name: '', description: '', effect: '' })
const factionForm = ref({ name: '', level: '', leader: '', territory: '', description: '' })
const locationForm = ref({ name: '', description: '' })
const itemForm = ref({ name: '', item_type: 'other', rarity: '', effect: '' })

const loadWorldview = async () => {
  try {
    const res = await api.get(`/api/novels/${novelId.value}/worldview`)
    if (res.data.power_system) {
      powerForm.value = {
        name: res.data.power_system.name || '',
        levels: res.data.power_system.levels || []
      }
    }
  } catch (error) {
    console.error('加载世界观失败:', error)
  }
}

const loadTechniques = async () => {
  try {
    const res = await api.get(`/api/novels/${novelId.value}/worldview/techniques`)
    techniques.value = res.data
  } catch (error) {
    console.error('加载功法失败:', error)
  }
}

const loadFactions = async () => {
  try {
    const res = await api.get(`/api/novels/${novelId.value}/worldview/factions`)
    factions.value = res.data
  } catch (error) {
    console.error('加载势力失败:', error)
  }
}

const loadLocations = async () => {
  try {
    const res = await api.get(`/api/novels/${novelId.value}/worldview/locations`)
    locations.value = res.data
  } catch (error) {
    console.error('加载地点失败:', error)
  }
}

const loadItems = async () => {
  try {
    const res = await api.get(`/api/novels/${novelId.value}/worldview/items`)
    items.value = res.data
  } catch (error) {
    console.error('加载物品失败:', error)
  }
}

const addLevel = () => {
  if (newLevel.value) {
    powerForm.value.levels.push(newLevel.value)
    newLevel.value = ''
  }
}

const removeLevel = (index) => {
  powerForm.value.levels.splice(index, 1)
}

const savePowerSystem = async () => {
  try {
    await api.put(`/api/novels/${novelId.value}/worldview/power-system`, powerForm.value)
    alert('保存成功')
  } catch (error) {
    console.error('保存失败:', error)
  }
}

const showTechniqueDialog = () => {
  techniqueForm.value = { name: '', level_name: '', description: '', effect: '' }
  techniqueDialogVisible.value = true
}

const createTechnique = async () => {
  try {
    await api.post(`/api/novels/${novelId.value}/worldview/techniques`, techniqueForm.value)
    techniqueDialogVisible.value = false
    loadTechniques()
  } catch (error) {
    console.error('创建失败:', error)
  }
}

const deleteTechnique = async (row) => {
  try {
    await api.delete(`/api/novels/${novelId.value}/worldview/techniques/${row.id}`)
    loadTechniques()
  } catch (error) {
    console.error('删除失败:', error)
  }
}

const showFactionDialog = () => {
  factionForm.value = { name: '', level: '', leader: '', territory: '', description: '' }
  factionDialogVisible.value = true
}

const createFaction = async () => {
  try {
    await api.post(`/api/novels/${novelId.value}/worldview/factions`, factionForm.value)
    factionDialogVisible.value = false
    loadFactions()
  } catch (error) {
    console.error('创建失败:', error)
  }
}

const deleteFaction = async (row) => {
  try {
    await api.delete(`/api/novels/${novelId.value}/worldview/factions/${row.id}`)
    loadFactions()
  } catch (error) {
    console.error('删除失败:', error)
  }
}

const showLocationDialog = () => {
  locationForm.value = { name: '', description: '' }
  locationDialogVisible.value = true
}

const createLocation = async () => {
  try {
    await api.post(`/api/novels/${novelId.value}/worldview/locations`, locationForm.value)
    locationDialogVisible.value = false
    loadLocations()
  } catch (error) {
    console.error('创建失败:', error)
  }
}

const deleteLocation = async (row) => {
  try {
    await api.delete(`/api/novels/${novelId.value}/worldview/locations/${row.id}`)
    loadLocations()
  } catch (error) {
    console.error('删除失败:', error)
  }
}

const showItemDialog = () => {
  itemForm.value = { name: '', item_type: 'other', rarity: '', effect: '' }
  itemDialogVisible.value = true
}

const createItem = async () => {
  try {
    await api.post(`/api/novels/${novelId.value}/worldview/items`, itemForm.value)
    itemDialogVisible.value = false
    loadItems()
  } catch (error) {
    console.error('创建失败:', error)
  }
}

const deleteItem = async (row) => {
  try {
    await api.delete(`/api/novels/${novelId.value}/worldview/items/${row.id}`)
    loadItems()
  } catch (error) {
    console.error('删除失败:', error)
  }
}

const checkConsistency = async () => {
  checking.value = true
  try {
    const res = await api.post(`/api/novels/${novelId.value}/worldview/check`)
    issues.value = res.data
  } catch (error) {
    console.error('检查失败:', error)
  } finally {
    checking.value = false
  }
}

const getItemTypeName = (type) => {
  const names = { artifact: '法宝', pill: '丹药', material: '材料', scripture: '功法', other: '其他' }
  return names[type] || type
}

onMounted(() => {
  loadWorldview()
  loadTechniques()
  loadFactions()
  loadLocations()
  loadItems()
})
</script>

<style scoped>
.worldview-manage {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
