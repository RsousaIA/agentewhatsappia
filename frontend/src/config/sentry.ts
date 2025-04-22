import * as Sentry from '@sentry/react'
import { BrowserTracing } from '@sentry/tracing'

Sentry.init({
  dsn: process.env.REACT_APP_SENTRY_DSN,
  integrations: [new BrowserTracing()],
  tracesSampleRate: 1.0,
  environment: process.env.NODE_ENV,
  release: process.env.REACT_APP_VERSION,
  beforeSend(event) {
    // Filtrar eventos de erro
    if (event.exception) {
      // Ignorar erros específicos
      if (event.exception.values?.[0].value?.includes('ChunkLoadError')) {
        return null
      }
    }
    return event
  }
})

// Função para capturar erros não tratados
export const captureError = (error: Error, context?: Record<string, any>) => {
  Sentry.captureException(error, {
    extra: context
  })
}

// Função para capturar mensagens
export const captureMessage = (message: string, level: Sentry.Severity = 'info') => {
  Sentry.captureMessage(message, level)
}

// Função para adicionar contexto ao erro
export const setContext = (name: string, context: Record<string, any>) => {
  Sentry.setContext(name, context)
}

// Função para adicionar tags ao erro
export const setTags = (tags: Record<string, string>) => {
  Sentry.setTags(tags)
} 