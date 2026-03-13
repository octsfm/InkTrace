<template>
  <div class="character-manage">
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>人物列表</span>
              <el-button type="primary" size="small" @click="showCreateDialog">添加人物</el-button>
            </div>
          </template>
          
          <el-input v-model="searchKeyword" placeholder="搜索人物" clearable style="margin-bottom: 15px;" />
          
          <el-tree
            :data="characterTree"
            :props="{ label: 'name', children: 'children' }"
            @node-click="selectCharacter"
            highlight-current
          >
            <template #default="{ node, data }">
              <span class="tree-node">
                <el-tag size="small" :type="getRoleType(data.role)">{{ getRoleName(data.role) }}</el-tag>
                <span style="margin-left: 8px;">{{ data.name }}</span>
              </span>
            </template>
          </el-tree>
        </el-card>
      </el-col>
      
      <el-col :span="16">
        <el-card v-if="selectedCharacter">
          <template #header>
            <span>{{ selectedCharacter.name }}</span>
            <el-button type="danger" size="small" style="float: right;" @click="deleteCharacter">删除</el-button>
          </template>
          
          <el-tabs>
            <el-tab-pane label="基本信息">
              <el-form :model="characterForm" label-width="80px">
                <el-row :gutter="20">
                  <el-col :span="12">
                    <el-form-item label="姓名">
                      <el-input v-model="characterForm.name" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="角色">
                      <el-select v-model="characterForm.role">
                        <el-option label="主角" value="protagonist" />
                        <el-option label="配角" value="supporting" />
                        <el-option label="反派" value="antagonist" />
                      </el-select>
                    </el-form-item>
                  </el-col>
                </el-row>
                <el-row :gutter="20">
                  <el-col :span="8">
                    <el-form-item label="年龄">
                      <el-input-number v-model="characterForm.age" :min="0" :max="10000" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="性别">
                      <el-input v-model="characterForm.gender" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="称号">
                      <el-input v-model="characterForm.title" />
                    </el-form-item>
                  </el-col>
                </el-row>
                <el-form-item label="外貌">
                  <el-input v-model="characterForm.appearance" type="textarea" :rows="2" />
                </el-form-item>
                <el-form-item label="性格">
                  <el-input v-model="characterForm.personality" type="textarea" :rows="2" />
                </el-form-item>
                <el-form-item label="背景">
                  <el-input v-model="characterForm.background" type="textarea" :rows="3" />
                </el-form-item>
                <el-form-item label="能力">
                  <el-tag v-for="ability in characterForm.abilities" :key="ability" closable @close="removeAbility(ability)">
                    {{ ability }}
                  </el-tag>
                  <el-input v-model="newAbility" @keyup.enter="addAbility" placeholder="添加能力" style="width: 150px; margin-left: 10px;" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="saveCharacter">保存</el-button>
                </el-form-item>
              </el-form>
            </el-tab-pane>
            
            <el-tab-pane label="人物关系">
              <el-button type="primary" size="small" @click="showRelationDialog" style="margin-bottom: 15px;">添加关系</el-button>
              <el-table :data="relations">
                <el-table-column prop="target_name" label="目标人物" />
                <el-table-column prop="relation_type" label="关系类型">
                  <template #default="{ row }">
                    {{ getRelationName(row.relation_type) }}
                  </template>
                </el-table-column>
                <el-table-column prop="description" label="描述" />
                <el-table-column label="操作" width="100">
                  <template #default="{ row }">
                    <el-button type="danger" size="small" @click="removeRelation(row)">删除</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-tab-pane>
            
            <el-tab-pane label="状态历史">
              <el-timeline>
                <el-timeline-item v-for="(state, index) in stateHistory" :key="index">
                  {{ state }}
                </el-timeline-item>
              </el-timeline>
              <el-input v-model="newState" placeholder="更新状态" @keyup.enter="updateState" style="margin-top: 15px;">
                <template #append>
                  <el-button @click="updateState">更新</el-button>
                </template>
              </el-input>
            </el-tab-pane>
          </el-tabs>
        </el-card>
        
        <el-empty v-else description="请选择人物" />
      </el-col>
    </el-row>
    
    <el-dialog v-model="createDialogVisible" title="添加人物" width="400px">
      <el-form :model="createForm" label-width="80px">
        <el-form-item label="姓名" required>
          <el-input v-model="createForm.name" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="createForm.role">
            <el-option label="主角" value="protagonist" />
            <el-option label="配角" value="supporting" />
            <el-option label="反派" value="antagonist" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createCharacter">创建</el-button>
      </template>
    </el-dialog>
    
    <el-dialog v-model="relationDialogVisible" title="添加关系" width="400px">
      <el-form :model="relationForm" label-width="80px">
        <el-form-item label="目标人物">
          <el-select v-model="relationForm.target_id" placeholder="选择人物">
            <el-option v-for="c in otherCharacters" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="关系类型">
          <el-select v-model="relationForm.relation_type">
            <el-option label="家人" value="family" />
            <el-option label="朋友" value="friend" />
            <el-option label="敌人" value="enemy" />
            <el-option label="恋人" value="lover" />
            <el-option label="师徒" value="master_disciple" />
            <el-option label="盟友" value="ally" />
            <el-option label="对手" value="rival" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="relationForm.description" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="relationDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="addRelation">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api'

const route = useRoute()
const novelId = computed(() => route.params.id)

const characters = ref([])
const selectedCharacter = ref(null)
const searchKeyword = ref('')
const createDialogVisible = ref(false)
const relationDialogVisible = ref(false)

const characterForm = ref({})
const createForm = ref({ name: '', role: 'supporting' })
const relationForm = ref({ target_id: '', relation_type: 'friend', description: '' })
const relations = ref([])
const stateHistory = ref([])
const newAbility = ref('')
const newState = ref('')

const characterTree = computed(() => {
  const filtered = searchKeyword.value
    ? characters.value.filter(c => c.name.includes(searchKeyword.value))
    : characters.value
  
  const groups = {
    protagonist: { name: '主角', children: [] },
    antagonist: { name: '反派', children: [] },
    supporting: { name: '配角', children: [] }
  }
  
  filtered.forEach(c => {
    if (groups[c.role]) {
      groups[c.role].children.push(c)
    }
  })
  
  return Object.values(groups).filter(g => g.children.length > 0)
})

const otherCharacters = computed(() => {
  return characters.value.filter(c => c.id !== selectedCharacter.value?.id)
})

const loadCharacters = async () => {
  try {
    const res = await api.get(`/api/novels/${novelId.value}/characters`)
    characters.value = res.data
  } catch (error) {
    console.error('加载人物失败:', error)
  }
}

const selectCharacter = (character) => {
  selectedCharacter.value = character
  characterForm.value = { ...character }
  loadRelations()
  loadStateHistory()
}

const loadRelations = async () => {
  if (!selectedCharacter.value) return
  try {
    const res = await api.get(`/api/novels/${novelId.value}/characters/${selectedCharacter.value.id}/relations`)
    relations.value = res.data.map(r => ({
      ...r,
      target_name: characters.value.find(c => c.id === r.target_id)?.name || r.target_id
    }))
  } catch (error) {
    console.error('加载关系失败:', error)
  }
}

const loadStateHistory = async () => {
  if (!selectedCharacter.value) return
  try {
    const res = await api.get(`/api/novels/${novelId.value}/characters/${selectedCharacter.value.id}/states`)
    stateHistory.value = res.data
  } catch (error) {
    console.error('加载状态历史失败:', error)
  }
}

const showCreateDialog = () => {
  createForm.value = { name: '', role: 'supporting' }
  createDialogVisible.value = true
}

const createCharacter = async () => {
  try {
    await api.post(`/api/novels/${novelId.value}/characters`, createForm.value)
    createDialogVisible.value = false
    loadCharacters()
  } catch (error) {
    console.error('创建人物失败:', error)
  }
}

const saveCharacter = async () => {
  try {
    await api.put(`/api/novels/${novelId.value}/characters/${selectedCharacter.value.id}`, characterForm.value)
    loadCharacters()
  } catch (error) {
    console.error('保存失败:', error)
  }
}

const deleteCharacter = async () => {
  try {
    await api.delete(`/api/novels/${novelId.value}/characters/${selectedCharacter.value.id}`)
    selectedCharacter.value = null
    loadCharacters()
  } catch (error) {
    console.error('删除失败:', error)
  }
}

const addAbility = () => {
  if (newAbility.value && !characterForm.value.abilities.includes(newAbility.value)) {
    characterForm.value.abilities.push(newAbility.value)
    newAbility.value = ''
  }
}

const removeAbility = (ability) => {
  characterForm.value.abilities = characterForm.value.abilities.filter(a => a !== ability)
}

const showRelationDialog = () => {
  relationForm.value = { target_id: '', relation_type: 'friend', description: '' }
  relationDialogVisible.value = true
}

const addRelation = async () => {
  try {
    await api.post(`/api/novels/${novelId.value}/characters/${selectedCharacter.value.id}/relations`, relationForm.value)
    relationDialogVisible.value = false
    loadRelations()
  } catch (error) {
    console.error('添加关系失败:', error)
  }
}

const removeRelation = async (relation) => {
  try {
    await api.delete(`/api/novels/${novelId.value}/characters/${selectedCharacter.value.id}/relations/${relation.target_id}`)
    loadRelations()
  } catch (error) {
    console.error('删除关系失败:', error)
  }
}

const updateState = async () => {
  if (!newState.value) return
  try {
    await api.post(`/api/novels/${novelId.value}/characters/${selectedCharacter.value.id}/state?state=${encodeURIComponent(newState.value)}`)
    newState.value = ''
    loadStateHistory()
  } catch (error) {
    console.error('更新状态失败:', error)
  }
}

const getRoleType = (role) => {
  const types = { protagonist: 'success', antagonist: 'danger', supporting: 'info' }
  return types[role] || 'info'
}

const getRoleName = (role) => {
  const names = { protagonist: '主角', antagonist: '反派', supporting: '配角' }
  return names[role] || role
}

const getRelationName = (type) => {
  const names = {
    family: '家人', friend: '朋友', enemy: '敌人', lover: '恋人',
    master_disciple: '师徒', ally: '盟友', rival: '对手'
  }
  return names[type] || type
}

onMounted(() => {
  loadCharacters()
})
</script>

<style scoped>
.character-manage {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tree-node {
  display: flex;
  align-items: center;
}
</style>
