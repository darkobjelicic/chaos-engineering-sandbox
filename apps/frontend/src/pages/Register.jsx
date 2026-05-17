import React, { useState } from 'react'
import axios from 'axios'
import { useNavigate } from 'react-router-dom'

export default function Register(){
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const r = await axios.post('http://localhost:8000/auth/register', { name, email, password })
      const token = r.data.access_token
      if (token) {
        localStorage.setItem('token', token)
        navigate('/')
      } else {
        setError('Registracija nije uspela')
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Greška pri registraciji')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{padding: 20, fontFamily: 'Arial, sans-serif', maxWidth: 600}}>
      <h1>✍️ Registracija</h1>
      <form onSubmit={handleSubmit}>
        <div style={{marginBottom: 10}}>
          <label>Ime i prezime</label>
          <input type="text" value={name} onChange={e=>setName(e.target.value)} placeholder="Vaše ime" required style={{padding: 8, width: '100%'}} />
        </div>
        <div style={{marginBottom: 10}}>
          <label>Email</label>
          <input type="email" value={email} onChange={e=>setEmail(e.target.value)} required style={{padding: 8, width: '100%'}} />
        </div>
        <div style={{marginBottom: 10}}>
          <label>Lozinka</label>
          <input type="password" value={password} onChange={e=>setPassword(e.target.value)} required style={{padding: 8, width: '100%'}} />
        </div>
        <button type="submit" disabled={loading} style={{padding: '8px 16px'}}>{loading ? '...' : 'Registruj se'}</button>
        {error && <p style={{color: 'red'}}>{error}</p>}
      </form>
    </div>
  )
}
