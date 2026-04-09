import React from 'react'
import ReactDOM from 'react-dom/client'
import { Provider } from 'react-redux'
import { BrowserRouter } from 'react-router-dom'
import App from './App.jsx'
import { store } from './features/store'
import { routerFuture } from './router/future'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Provider store={store}>
      <BrowserRouter future={routerFuture}>
        <App />
      </BrowserRouter>
    </Provider>
  </React.StrictMode>,
)
