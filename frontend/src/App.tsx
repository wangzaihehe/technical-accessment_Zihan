import { useState } from 'react'
import axios from 'axios'

interface AuthComponent {
  found: boolean
  htmlSnippet?: string
  formElement?: string
  usernameInput?: string
  passwordInput?: string
  submitButton?: string
  method?: string
  action?: string
}

interface ScrapeResult {
  url: string
  success: boolean
  error?: string
  authComponent?: AuthComponent
}

function App() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ScrapeResult | null>(null)
  const [predefinedResults, setPredefinedResults] = useState<ScrapeResult[]>([])
  const [loadingPredefined, setLoadingPredefined] = useState(false)
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set())

  const toggleExpand = (sectionId: string) => {
    const newExpanded = new Set(expandedSections)
    if (newExpanded.has(sectionId)) {
      newExpanded.delete(sectionId)
    } else {
      newExpanded.add(sectionId)
    }
    setExpandedSections(newExpanded)
  }

  const isLongContent = (content: string, maxLength: number = 500) => {
    return content && content.length > maxLength
  }

  const renderCodeBlock = (content: string, sectionId: string, className: string = '') => {
    if (!content) return null
    
    const isLong = isLongContent(content)
    const isExpanded = expandedSections.has(sectionId)
    
    if (!isLong) {
      // Short content: display directly
      return (
        <pre className={`bg-gray-800 text-green-400 p-4 rounded-lg overflow-x-auto text-sm ${className}`}>
          {content}
        </pre>
      )
    }
    
    // Long content: display with fixed height, expandable
    return (
      <div>
        <pre className={`bg-gray-800 text-green-400 p-4 rounded-lg overflow-x-auto text-sm ${className} ${!isExpanded ? 'max-h-48 overflow-y-hidden' : ''}`}>
          {content}
        </pre>
        <button
          onClick={() => toggleExpand(sectionId)}
          className="mt-2 text-sm text-indigo-600 hover:text-indigo-800 font-medium cursor-pointer"
        >
          {isExpanded ? '▲ Collapse' : '▼ Expand to see full content'}
        </button>
      </div>
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url.trim()) {
      alert('Please enter a URL')
      return
    }

    setLoading(true)
    setResult(null)

    try {
      const response = await axios.post('/api/scrape', { url: url.trim() })
      setResult(response.data)
    } catch (error: any) {
      setResult({
        url: url.trim(),
        success: false,
        error: error.response?.data?.detail || error.response?.data?.error || 'Request failed',
      })
    } finally {
      setLoading(false)
    }
  }

  const handlePredefinedScrape = async () => {
    setLoadingPredefined(true)
    setPredefinedResults([])

    try {
      const response = await axios.get('/api/predefined')
      setPredefinedResults(response.data.results || [])
    } catch (error: any) {
      console.error('Failed to scrape predefined websites:', error)
      alert('Failed to scrape predefined websites: ' + (error.response?.data?.detail || error.response?.data?.error || 'Unknown error'))
    } finally {
      setLoadingPredefined(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Website Authentication Component Detector
          </h1>
          <p className="text-lg text-gray-600">
            Automatically detect login forms and authentication components in web pages
          </p>
        </div>

        {/* Dynamic URL Input Section */}
        <div className="bg-white rounded-lg shadow-xl p-8 mb-8">
          <h2 className="text-2xl font-semibold text-gray-800 mb-6">
            Enter Website URL
          </h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="flex gap-4">
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="Enter website URL, e.g., https://example.com"
                className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
                disabled={loading}
              />
              <button
                type="submit"
                disabled={loading}
                className="px-8 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium transition-colors"
              >
                {loading ? 'Detecting...' : 'Detect'}
              </button>
            </div>
          </form>

          {/* Results Display */}
          {result && (
            <div className="mt-8 p-6 bg-gray-50 rounded-lg border border-gray-200">
              <h3 className="text-xl font-semibold text-gray-800 mb-4">
                Detection Result: {result.url}
              </h3>
              
              {result.success ? (
                result.authComponent?.found ? (
                  <div className="space-y-4">
                    <div className="flex items-center gap-2">
                      <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
                        Authentication Component Found
                      </span>
                    </div>
                    
                    {result.authComponent.formElement && (
                      <div>
                        <h4 className="font-semibold text-gray-700 mb-2">Form Element:</h4>
                        {renderCodeBlock(result.authComponent.formElement, `single-form-${result.url}`)}
                      </div>
                    )}

                    {result.authComponent.htmlSnippet && (
                      <div>
                        <h4 className="font-semibold text-gray-700 mb-2">HTML Snippet:</h4>
                        {renderCodeBlock(result.authComponent.htmlSnippet, `single-html-${result.url}`)}
                      </div>
                    )}

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {result.authComponent.usernameInput && (
                        <div>
                          <h4 className="font-semibold text-gray-700 mb-2">Username Input:</h4>
                          {renderCodeBlock(result.authComponent.usernameInput, `single-username-${result.url}`, 'p-3')}
                        </div>
                      )}
                      
                      {result.authComponent.passwordInput && (
                        <div>
                          <h4 className="font-semibold text-gray-700 mb-2">Password Input:</h4>
                          {renderCodeBlock(result.authComponent.passwordInput, `single-password-${result.url}`, 'p-3')}
                        </div>
                      )}
                    </div>

                    {result.authComponent.submitButton && (
                      <div>
                        <h4 className="font-semibold text-gray-700 mb-2">Submit Button:</h4>
                        {renderCodeBlock(result.authComponent.submitButton, `single-submit-${result.url}`, 'p-3')}
                      </div>
                    )}

                    {(result.authComponent.method || result.authComponent.action) && (
                      <div className="text-sm text-gray-600">
                        <p><strong>Method:</strong> {result.authComponent.method || 'N/A'}</p>
                        <p><strong>Action:</strong> {result.authComponent.action || 'N/A'}</p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <span className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full text-sm font-medium">
                      No Authentication Component Found
                    </span>
                    <p className="text-gray-600">This page does not contain a login form or authentication component</p>
                  </div>
                )
              ) : (
                <div className="flex items-center gap-2">
                  <span className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-sm font-medium">
                    Error
                  </span>
                  <p className="text-red-600">{result.error}</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Predefined Websites Scraping Section */}
        <div className="bg-white rounded-lg shadow-xl p-8">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-semibold text-gray-800">
              Predefined Websites Detection
            </h2>
            <button
              onClick={handlePredefinedScrape}
              disabled={loadingPredefined}
              className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium transition-colors"
            >
              {loadingPredefined ? 'Detecting...' : 'Detect 5 Predefined Websites'}
            </button>
          </div>

          {predefinedResults.length > 0 && (
            <div className="space-y-6">
              {predefinedResults.map((result, index) => (
                <div
                  key={index}
                  className="p-6 bg-gray-50 rounded-lg border border-gray-200"
                >
                  <h3 className="text-xl font-semibold text-gray-800 mb-4">
                    Detection Result: {result.url}
                  </h3>
                  
                  {result.success ? (
                    result.authComponent?.found ? (
                      <div className="space-y-4">
                        <div className="flex items-center gap-2">
                          <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
                            Authentication Component Found
                          </span>
                        </div>
                        
                        {result.authComponent.formElement && (
                          <div>
                            <h4 className="font-semibold text-gray-700 mb-2">Form Element:</h4>
                            {renderCodeBlock(result.authComponent.formElement, `predefined-form-${index}-${result.url}`)}
                          </div>
                        )}

                        {result.authComponent.htmlSnippet && (
                          <div>
                            <h4 className="font-semibold text-gray-700 mb-2">HTML Snippet:</h4>
                            {renderCodeBlock(result.authComponent.htmlSnippet, `predefined-html-${index}-${result.url}`)}
                          </div>
                        )}

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {result.authComponent.usernameInput && (
                            <div>
                              <h4 className="font-semibold text-gray-700 mb-2">Username Input:</h4>
                              {renderCodeBlock(result.authComponent.usernameInput, `predefined-username-${index}-${result.url}`, 'p-3')}
                            </div>
                          )}
                          
                          {result.authComponent.passwordInput && (
                            <div>
                              <h4 className="font-semibold text-gray-700 mb-2">Password Input:</h4>
                              {renderCodeBlock(result.authComponent.passwordInput, `predefined-password-${index}-${result.url}`, 'p-3')}
                            </div>
                          )}
                        </div>

                        {result.authComponent.submitButton && (
                          <div>
                            <h4 className="font-semibold text-gray-700 mb-2">Submit Button:</h4>
                            {renderCodeBlock(result.authComponent.submitButton, `predefined-submit-${index}-${result.url}`, 'p-3')}
                          </div>
                        )}

                        {(result.authComponent.method || result.authComponent.action) && (
                          <div className="text-sm text-gray-600">
                            <p><strong>Method:</strong> {result.authComponent.method || 'N/A'}</p>
                            <p><strong>Action:</strong> {result.authComponent.action || 'N/A'}</p>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <span className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full text-sm font-medium">
                          No Authentication Component Found
                        </span>
                        <p className="text-gray-600">This page does not contain a login form or authentication component</p>
                      </div>
                    )
                  ) : (
                    <div className="flex items-center gap-2">
                      <span className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-sm font-medium">
                        Error
                      </span>
                      <p className="text-red-600">{result.error}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default App

