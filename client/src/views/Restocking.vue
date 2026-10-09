<template>
  <div class="orders">
    <div class="page-header">
      <h2>Restocking</h2>
      <p>Set your budget and review demand-based recommendations.</p>
    </div>

    <div class="success-banner" v-if="orderSuccess">
      Restocking order submitted successfully. Check the Orders tab to track delivery.
    </div>

    <div v-if="loading">Loading...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <!-- Budget slider card -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Budget</h3>
        </div>
        <div class="budget-control">
          <input
            type="range"
            min="0"
            max="100000"
            step="1000"
            v-model.number="budget"
            class="budget-slider"
          />
          <div class="budget-labels">
            <span>$0</span>
            <span class="budget-current">${{ budget.toLocaleString() }}</span>
            <span>$100,000</span>
          </div>
        </div>
      </div>

      <!-- Summary stat cards -->
      <div class="stats-grid">
        <div class="stat-card info">
          <div class="stat-label">Budget</div>
          <div class="stat-value">${{ budget.toLocaleString() }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">Items to Restock</div>
          <div class="stat-value">{{ recommendations.length }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">Total Cost</div>
          <div class="stat-value">${{ Math.round(totalCost).toLocaleString() }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Remaining Budget</div>
          <div class="stat-value">${{ Math.round(remainingBudget).toLocaleString() }}</div>
        </div>
      </div>

      <!-- Recommendations table -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Recommendations ({{ recommendations.length }})</h3>
          <button
            class="btn-primary"
            @click="placeOrder"
            :disabled="recommendations.length === 0"
          >
            Place Order
          </button>
        </div>
        <div v-if="recommendations.length === 0" class="empty-state">
          No items to restock within this budget. Try increasing the budget.
        </div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>Item Name</th>
                <th>SKU</th>
                <th>Demand Gap</th>
                <th>Qty to Order</th>
                <th>Unit Cost</th>
                <th>Line Total</th>
                <th>Trend</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in recommendations" :key="item.item_sku">
                <td><strong>{{ item.item_name }}</strong></td>
                <td>{{ item.item_sku }}</td>
                <td>{{ item.gap }}</td>
                <td>{{ item.qty_to_order }}</td>
                <td>${{ item.unit_cost.toFixed(2) }}</td>
                <td><strong>${{ Math.round(item.line_total).toLocaleString() }}</strong></td>
                <td>
                  <span
                    :class="['badge', item.trend === 'Up' ? 'success' : item.trend === 'Down' ? 'danger' : 'info']"
                  >
                    {{ item.trend }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'

export default {
  name: 'Restocking',
  setup() {
    const budget = ref(10000)
    const forecasts = ref([])
    const inventoryItems = ref([])
    const loading = ref(true)
    const error = ref(null)
    const orderSuccess = ref(false)

    onMounted(async () => {
      try {
        const [forecastData, inventoryData] = await Promise.all([
          api.getDemandForecasts(),
          api.getInventory()
        ])
        forecasts.value = forecastData
        inventoryItems.value = inventoryData
      } catch (err) {
        error.value = 'Failed to load data: ' + err.message
      } finally {
        loading.value = false
      }
    })

    // Join by SKU: for each forecast, find matching inventory item.
    // Greedy allocation fills highest-demand-gap items first until budget runs out.
    const recommendations = computed(() => {
      const costMap = {}
      for (const inv of inventoryItems.value) {
        costMap[inv.sku] = inv.unit_cost
      }

      const candidates = forecasts.value
        .filter(f => f.forecasted_demand > f.current_demand && costMap[f.item_sku] != null)
        .map(f => ({
          ...f,
          gap: f.forecasted_demand - f.current_demand,
          unit_cost: costMap[f.item_sku]
        }))
        .sort((a, b) => b.gap - a.gap) // highest gap first

      let remaining = budget.value
      const result = []
      for (const item of candidates) {
        if (item.unit_cost > remaining) continue // can't afford even 1
        const qty = Math.min(item.gap, Math.floor(remaining / item.unit_cost))
        if (qty <= 0) continue
        remaining -= qty * item.unit_cost
        result.push({ ...item, qty_to_order: qty, line_total: qty * item.unit_cost })
        if (remaining < 1) break // budget exhausted
      }
      return result
    })

    const totalCost = computed(() =>
      recommendations.value.reduce((s, r) => s + r.line_total, 0)
    )

    const remainingBudget = computed(() => budget.value - totalCost.value)

    const placeOrder = async () => {
      try {
        const items = recommendations.value.map(r => ({
          item_sku: r.item_sku,
          item_name: r.item_name,
          quantity: r.qty_to_order,
          unit_cost: r.unit_cost
        }))
        await api.createRestockingOrder(items)
        orderSuccess.value = true
        // Reset success banner after 4 seconds
        setTimeout(() => { orderSuccess.value = false }, 4000)
      } catch (err) {
        error.value = 'Failed to place order: ' + err.message
      }
    }

    return {
      budget,
      forecasts,
      inventoryItems,
      loading,
      error,
      orderSuccess,
      recommendations,
      totalCost,
      remainingBudget,
      placeOrder
    }
  }
}
</script>

<style scoped>
.budget-control {
  padding: 1rem 0;
}

.budget-slider {
  width: 100%;
  accent-color: #2563eb;
  height: 6px;
}

.budget-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
  font-size: 0.875rem;
  color: #64748b;
}

.budget-current {
  font-weight: 600;
  color: #0f172a;
}

.btn-primary {
  background: #2563eb;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
}

.btn-primary:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-primary:not(:disabled):hover {
  background: #1d4ed8;
}

.success-banner {
  background: #f0fdf4;
  border: 1px solid #86efac;
  color: #166534;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
}

.empty-state {
  padding: 2rem;
  text-align: center;
  color: #64748b;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
