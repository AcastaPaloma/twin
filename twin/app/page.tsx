'use client'

/* eslint-disable @typescript-eslint/no-explicit-any */

import React, { useState, useEffect } from 'react'

// Declare chrome global for TypeScript
declare global {
  interface Window {
    chrome: any
  }
  var chrome: any
}

interface User {
  id: string
  email: string
  is_active: boolean
}

const Home = () => {
  const [user, setUser] = useState<User | null>(null)
  const [trackingEnabled, setTrackingEnabled] = useState(true)
  const [loading, setLoading] = useState(true)
  const [loginEmail, setLoginEmail] = useState('')
  const [loginLoading, setLoginLoading] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    loadInitialData()
  }, [])

  const loadInitialData = async () => {
    try {
      // Check if this is running in extension context
      if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.sendMessage) {
        // Get current user
        chrome.runtime.sendMessage({ type: 'GET_USER' }, (response: any) => {
          if (response && response.user) {
            setUser(response.user)
          }
        })

        // Get tracking status
        chrome.runtime.sendMessage({ type: 'GET_TRACKING_STATUS' }, (response: any) => {
          if (response) {
            setTrackingEnabled(response.enabled)
          }
        })
      }
    } catch (error) {
      console.error('Error loading data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!loginEmail.trim()) return

    setLoginLoading(true)
    setMessage('')

    try {
      if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.sendMessage) {
        chrome.runtime.sendMessage({
          type: 'LOGIN',
          email: loginEmail.trim()
        }, (response: any) => {
          setLoginLoading(false)
          if (response && response.success) {
            setUser(response.user)
            setLoginEmail('')
            setMessage(response.isNew ? 'Account created and logged in!' : 'Logged in successfully!')
          } else {
            setMessage('Login failed: ' + (response?.error || 'Unknown error'))
          }
        })
      } else {
        setLoginLoading(false)
        setMessage('Extension not available')
      }
    } catch (error) {
      setLoginLoading(false)
      setMessage('Login error: ' + error)
    }
  }

  const handleLogout = async () => {
    try {
      if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.sendMessage) {
        chrome.runtime.sendMessage({ type: 'LOGOUT' }, (response: any) => {
          if (response && response.success) {
            setUser(null)
            setMessage('Logged out successfully')
          }
        })
      }
    } catch (error) {
      setMessage('Logout error: ' + error)
    }
  }

  const toggleTracking = async () => {
    const newStatus = !trackingEnabled
    setTrackingEnabled(newStatus)

    try {
      if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.sendMessage) {
        chrome.runtime.sendMessage({
          type: 'TOGGLE_TRACKING',
          enabled: newStatus
        })
      }
    } catch (error) {
      console.error('Error toggling tracking:', error)
    }
  }

  if (loading) {
    return (
      <div className="w-80 h-96 p-4 bg-white">
        <div className="flex items-center justify-center h-full">
          <div className="text-gray-500">Loading...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="w-80 h-96 p-4 bg-white">
      {/* Header */}
      <div className="mb-4 pb-2 border-b">
        <h1 className="text-lg font-bold text-gray-800">Twin Tracker</h1>
      </div>

      {/* Message */}
      {message && (
        <div className={`text-xs p-2 rounded mb-3 ${
          message.includes('error') || message.includes('failed')
            ? 'bg-red-50 text-red-700 border border-red-200'
            : 'bg-green-50 text-green-700 border border-green-200'
        }`}>
          {message}
        </div>
      )}

      {/* Not Logged In */}
      {!user && (
        <div className="space-y-4">
          <div className="text-sm text-gray-600 text-center">
            Please log in to start tracking your activity
          </div>

          <form onSubmit={handleLogin} className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email Address
              </label>
              <input
                type="email"
                value={loginEmail}
                onChange={(e) => setLoginEmail(e.target.value)}
                placeholder="Enter your email"
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                required
                disabled={loginLoading}
              />
            </div>

            <button
              type="submit"
              disabled={loginLoading || !loginEmail.trim()}
              className="w-full bg-blue-500 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              {loginLoading ? 'Logging in...' : 'Login / Sign Up'}
            </button>
          </form>
        </div>
      )}

      {/* Logged In */}
      {user && (
        <div className="space-y-4">
          {/* User Info */}
          <div className="bg-gray-50 p-3 rounded">
            <div className="text-sm font-medium text-gray-800">Logged in as:</div>
            <div className="text-sm text-gray-600">{user.email}</div>
          </div>

          {/* Tracking Status */}
          <div className="flex items-center justify-between p-3 border border-gray-200 rounded">
            <div className="flex-1">
              <div className="text-sm font-medium text-gray-800">Activity Tracking</div>
              <div className="text-xs text-gray-600">
                {trackingEnabled ? 'Currently tracking your browsing' : 'Tracking is paused'}
              </div>
            </div>
            <button
              onClick={toggleTracking}
              className={`w-12 h-6 rounded-full transition-colors ${
                trackingEnabled ? 'bg-green-500' : 'bg-gray-300'
              }`}
            >
              <div
                className={`w-5 h-5 bg-white rounded-full transition-transform ${
                  trackingEnabled ? 'translate-x-6' : 'translate-x-0.5'
                }`}
              />
            </button>
          </div>

          {/* Status Indicator */}
          <div className={`text-xs p-2 rounded text-center ${
            trackingEnabled
              ? 'bg-green-50 text-green-700 border border-green-200'
              : 'bg-yellow-50 text-yellow-700 border border-yellow-200'
          }`}>
            {trackingEnabled ? '🟢 Actively tracking searches and browsing' : '⏸️ Tracking paused'}
          </div>

          {/* Logout Button */}
          <button
            onClick={handleLogout}
            className="w-full bg-gray-500 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-gray-600"
          >
            Logout
          </button>
        </div>
      )}

      {/* Footer */}
      <div className="text-xs text-gray-400 text-center mt-4 pt-2 border-t">
        Twin v0.0.1 - Activity Tracker
      </div>
    </div>
  )
}

export default Home