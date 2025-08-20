import { useState } from 'react'
import { 
  DocumentTextIcon,
  HomeIcon,
  TagIcon,
  ShoppingBagIcon,
  ClipboardDocumentListIcon,
  PhotoIcon,
  DocumentIcon,
  EllipsisHorizontalIcon,
  CheckIcon,
  InformationCircleIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline'
import { DiscoveredPage, PageType, PageCategory, Priority } from '@types/index'
import { motion, AnimatePresence } from 'framer-motion'

interface PagesListProps {
  pages: DiscoveredPage[]
  showSelection?: boolean
  showMetadata?: boolean
  maxHeight?: string
  onPageSelect?: (pageUrl: string) => void
  onSelectionChange?: (selectedPages: string[]) => void
}

export function PagesList({ 
  pages, 
  showSelection = false, 
  showMetadata = false,
  maxHeight = '500px',
  onPageSelect,
  onSelectionChange
}: PagesListProps) {
  const [sortBy, setSortBy] = useState<'url' | 'type' | 'category' | 'priority'>('category')
  const [filterBy, setFilterBy] = useState<PageType | 'all'>('all')
  const [showDetails, setShowDetails] = useState<string | null>(null)
  
  // Get icon for page type
  const getPageTypeIcon = (type: PageType) => {
    switch (type) {
      case PageType.HOME:
        return HomeIcon
      case PageType.CATEGORY:
        return TagIcon
      case PageType.PRODUCT:
        return ShoppingBagIcon
      case PageType.CONTENT:
        return DocumentTextIcon
      case PageType.FORM:
        return ClipboardDocumentListIcon
      case PageType.MEDIA:
        return PhotoIcon
      case PageType.DOCUMENT:
        return DocumentIcon
      default:
        return DocumentTextIcon
    }
  }
  
  // Get badge style for category
  const getCategoryBadge = (category: PageCategory) => {
    switch (category) {
      case PageCategory.CRITICAL:
        return 'badge-error'
      case PageCategory.IMPORTANT:
        return 'badge-warning'
      case PageCategory.REPRESENTATIVE:
        return 'badge-info'
      default:
        return 'badge-success opacity-70'
    }
  }
  
  // Get priority indicator
  const getPriorityIndicator = (priority: Priority) => {
    switch (priority) {
      case Priority.HIGH:
        return { color: 'bg-error-500', text: 'Alta' }
      case Priority.MEDIUM:
        return { color: 'bg-warning-500', text: 'Media' }
      default:
        return { color: 'bg-success-500', text: 'Bassa' }
    }
  }
  
  // Sort and filter pages
  const processedPages = pages
    .filter(page => filterBy === 'all' || page.page_type === filterBy)
    .sort((a, b) => {
      switch (sortBy) {
        case 'type':
          return a.page_type.localeCompare(b.page_type)
        case 'category':
          const categoryOrder = { [PageCategory.CRITICAL]: 0, [PageCategory.IMPORTANT]: 1, [PageCategory.REPRESENTATIVE]: 2, [PageCategory.OPTIONAL]: 3 }
          return categoryOrder[a.category] - categoryOrder[b.category]
        case 'priority':
          const priorityOrder = { [Priority.HIGH]: 0, [Priority.MEDIUM]: 1, [Priority.LOW]: 2 }
          return priorityOrder[a.priority] - priorityOrder[b.priority]
        default:
          return a.url.localeCompare(b.url)
      }
    })
  
  const handlePageToggle = (pageUrl: string) => {
    if (onPageSelect) {
      onPageSelect(pageUrl)
    }
  }
  
  const selectedCount = pages.filter(p => p.selected).length
  
  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center space-x-4">
          {/* Sort */}
          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-700">Ordina per:</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="text-sm border border-gray-300 rounded px-2 py-1 focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="category">Categoria</option>
              <option value="type">Tipo</option>
              <option value="priority">Priorità</option>
              <option value="url">URL</option>
            </select>
          </div>
          
          {/* Filter */}
          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-700">Filtra:</label>
            <select
              value={filterBy}
              onChange={(e) => setFilterBy(e.target.value as any)}
              className="text-sm border border-gray-300 rounded px-2 py-1 focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="all">Tutte</option>
              <option value={PageType.HOME}>Homepage</option>
              <option value={PageType.CATEGORY}>Categorie</option>
              <option value={PageType.PRODUCT}>Prodotti</option>
              <option value={PageType.CONTENT}>Contenuti</option>
              <option value={PageType.FORM}>Form</option>
              <option value={PageType.MEDIA}>Media</option>
              <option value={PageType.DOCUMENT}>Documenti</option>
            </select>
          </div>
        </div>
        
        {/* Stats */}
        <div className="text-sm text-gray-500">
          {processedPages.length} di {pages.length} pagine
          {showSelection && selectedCount > 0 && (
            <span className="ml-2 text-primary-600 font-medium">
              ({selectedCount} selezionate)
            </span>
          )}
        </div>
      </div>
      
      {/* Pages List */}
      <div 
        className="space-y-2 overflow-y-auto scrollbar-thin"
        style={{ maxHeight }}
      >
        <AnimatePresence>
          {processedPages.map((page) => {
            const IconComponent = getPageTypeIcon(page.page_type)
            const priorityInfo = getPriorityIndicator(page.priority)
            const isExpanded = showDetails === page.url
            
            return (
              <motion.div
                key={page.url}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className={`bg-white border rounded-lg transition-all duration-200 hover:shadow-md ${
                  showSelection && page.selected ? 'ring-2 ring-primary-500 border-primary-200' : 'border-gray-200'
                }`}
              >
                <div className="p-4">
                  <div className="flex items-start space-x-3">
                    {/* Selection Checkbox */}
                    {showSelection && (
                      <label className="flex items-center mt-1">
                        <input
                          type="checkbox"
                          checked={page.selected}
                          onChange={() => handlePageToggle(page.url)}
                          className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                        />
                      </label>
                    )}
                    
                    {/* Page Icon */}
                    <div className="flex-shrink-0 mt-0.5">
                      <IconComponent className="h-5 w-5 text-gray-400" />
                    </div>
                    
                    {/* Page Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <h4 className="text-sm font-medium text-gray-900 truncate">
                            {page.title || 'Pagina senza titolo'}
                          </h4>
                          <p className="text-xs text-gray-500 truncate mt-1 font-mono">
                            {page.url}
                          </p>
                        </div>
                        
                        {/* Badges and Actions */}
                        <div className="flex items-center space-x-2 ml-4">
                          <span className={`${getCategoryBadge(page.category)} capitalize`}>
                            {page.category}
                          </span>
                          
                          <div className={`w-2 h-2 rounded-full ${priorityInfo.color}`} title={`Priorità ${priorityInfo.text}`} />
                          
                          {showMetadata && (
                            <button
                              onClick={() => setShowDetails(isExpanded ? null : page.url)}
                              className="text-gray-400 hover:text-gray-600 transition-colors"
                            >
                              <InformationCircleIcon className="h-4 w-4" />
                            </button>
                          )}
                        </div>
                      </div>
                      
                      {/* Quick metadata row */}
                      <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                        <span>Tipo: {page.page_type}</span>
                        <span>Depth: {page.depth}</span>
                        {page.metadata.form_count > 0 && (
                          <span className="text-primary-600 font-medium">
                            {page.metadata.form_count} form
                          </span>
                        )}
                        {page.accessibility_hints.length > 0 && (
                          <span className="text-warning-600 font-medium">
                            {page.accessibility_hints.length} avvisi
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  {/* Expanded Details */}
                  {isExpanded && showMetadata && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      className="mt-4 pt-4 border-t border-gray-100"
                    >
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                        <div>
                          <span className="text-gray-500">Parole:</span>
                          <div className="font-medium">{page.metadata.word_count}</div>
                        </div>
                        <div>
                          <span className="text-gray-500">Immagini:</span>
                          <div className="font-medium">{page.metadata.image_count}</div>
                        </div>
                        <div>
                          <span className="text-gray-500">Link:</span>
                          <div className="font-medium">{page.metadata.link_count}</div>
                        </div>
                        <div>
                          <span className="text-gray-500">Complessità:</span>
                          <div className="font-medium">{Math.round(page.metadata.estimated_complexity * 100)}%</div>
                        </div>
                      </div>
                      
                      {/* Accessibility Hints */}
                      {page.accessibility_hints.length > 0 && (
                        <div className="mt-3">
                          <h5 className="text-xs font-medium text-gray-700 mb-2">Potenziali Problemi:</h5>
                          <div className="space-y-1">
                            {page.accessibility_hints.map((hint, index) => (
                              <div key={index} className="flex items-start space-x-2">
                                <ExclamationTriangleIcon className={`h-3 w-3 mt-0.5 flex-shrink-0 ${
                                  hint.type === 'potential_issue' ? 'text-error-500' :
                                  hint.type === 'warning' ? 'text-warning-500' :
                                  'text-primary-500'
                                }`} />
                                <span className="text-xs text-gray-600">{hint.message}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </motion.div>
                  )}
                </div>
              </motion.div>
            )
          })}
        </AnimatePresence>
        
        {processedPages.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            <DocumentTextIcon className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <p>Nessuna pagina trovata con i filtri selezionati</p>
          </div>
        )}
      </div>
    </div>
  )
}