import React, { useState } from 'react'
import axios from 'axios'
import { useNavigate } from 'react-router-dom'

export default function Login(){
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      params.append('username', email)
      params.append('password', password)
      const r = await axios.post('http://localhost:8000/auth/login', params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      })
      const token = r.data.access_token
      if (token) {
        localStorage.setItem('token', token)
        navigate('/')
      } else {
        setError('Login nije uspeo')
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Greška pri logovanju')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{padding: 20, fontFamily: 'Arial, sans-serif', maxWidth: 600}}>
      <h1>🔐 Prijava</h1>
      <form onSubmit={handleSubmit}>
        <div style={{marginBottom: 10}}>
          <label>Email</label>
          <input type="email" value={email} onChange={e=>setEmail(e.target.value)} required style={{padding: 8, width: '100%'}} />
        </div>
        <div style={{marginBottom: 10}}>
          <label>Lozinka</label>
          <input type="password" value={password} onChange={e=>setPassword(e.target.value)} required style={{padding: 8, width: '100%'}} />
        </div>
        <button type="submit" disabled={loading} style={{padding: '8px 16px'}}>{loading ? '...' : 'Prijavi se'}</button>
        {error && <p style={{color: 'red'}}>{error}</p>}
      </form>
    </div>
  )
}
