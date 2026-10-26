// Re-export all API functions grouped by domain

// Accounts
export {
  getAccounts,
  updateAccount,
  getCreditCardDues,
} from './accounts'

// Categories
export {
  getCategories,
  createCategory,
  updateCategory,
  deleteCategory,
  deleteCategoryCascade,
  getCategoryTransactions,
  moveCategoryTransactions,
} from './categories'

// Budgets
export {
  getBudgetStatus,
  setBudget,
  deleteBudget,
  copyBudgets,
} from './budgets'

// Transactions
export {
  getTransactions,
  createTransaction,
  updateTransaction,
  deleteTransaction,
  detectTransfers,
} from './transactions'

// Rules
export {
  getRules,
  createRule,
  deleteRule,
  applyRules,
  suggestPattern,
} from './rules'

// Imports
export {
  getAiStatus,
  importFiles,
  previewImport,
  getImportHistory,
  revertImport,
} from './imports'

// Reports
export {
  getProfitLoss,
  getYtdProfitLoss,
} from './reports'

// Legacy compatibility - single api object
// TODO: Remove after all pages are migrated
import * as accounts from './accounts'
import * as categories from './categories'
import * as budgets from './budgets'
import * as transactions from './transactions'
import * as rules from './rules'
import * as imports from './imports'
import * as reports from './reports'

export const api = {
  ...accounts,
  ...categories,
  ...budgets,
  ...transactions,
  ...rules,
  ...imports,
  ...reports,
}
