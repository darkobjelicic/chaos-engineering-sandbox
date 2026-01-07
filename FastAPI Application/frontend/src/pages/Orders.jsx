import React, { useEffect, useState } from 'react'
import axios from 'axios'

// Mock korisnički podaci
const mockUsers = {
  1: 'Alice',
  2: 'Bob',
  3: 'Charlie',
  4: 'Diana',
  5: 'Eve'
}

export default function Orders(){
  const [orders, setOrders] = useState([])
  const [books, setBooks] = useState([])
  const [currentUser, setCurrentUser] = useState(null)
  const [displayName, setDisplayName] = useState(null)
  const [loading, setLoading] = useState(true)
  const [booksLoading, setBooksLoading] = useState(true)
  const [error, setError] = useState(null)
  const [formData, setFormData] = useState({
    user_id: 1,
    book_id: 1,
    quantity: 1
  })
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState(null)
  const [submitSuccess, setSubmitSuccess] = useState(false)

  // Učitaj knjige
  useEffect(()=>{
    axios.get('http://localhost:8000/books')
      .then(r=> {
        setBooks(r.data || [])
        setBooksLoading(false)
      })
      .catch(err=> {
        console.error('Greška pri učitavanju knjiga:', err)
        setBooksLoading(false)
      })
  },[])

  // Učitaj narudžbine (pokreni i kada se promeni trenutni korisnik)
  useEffect(()=>{
    loadOrders()
  },[currentUser])

  const loadOrders = () => {
    setLoading(true)
    const token = localStorage.getItem('token')
    const headers = token ? { Authorization: `Bearer ${token}` } : {}

    axios.get('http://localhost:8000/orders', { headers })
      .then(r=> {
        const all = r.data || []
        if (currentUser && currentUser.id) {
          setOrders(all.filter(o => o.user_id === currentUser.id))
        } else {
          setOrders(all)
        }
        setLoading(false)
      })
      .catch(err=> {
        console.error('Greška pri učitavanju narudžbina:', err)
        setError('Nije moguće učitati narudžbine')
        setLoading(false)
      })
  }

  // Učitaj trenutnog korisnika (ako je ulogovan)
  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) return
    axios.get('http://localhost:8000/auth/me', { headers: { Authorization: `Bearer ${token}` } })
      .then(r => setCurrentUser(r.data))
      .catch(err => console.warn('Ne mogu dohvatiti trenutnog korisnika:', err))
  }, [])

  // Derive a friendly display name once we have currentUser
  useEffect(() => {
    if (!currentUser) {
      setDisplayName(null)
      return
    }

    // Prefer an explicit 'name' field if present; otherwise derive from email
    if (currentUser.name) {
      setDisplayName(currentUser.name)
      return
    }

    // Derive name from email local-part (before @), handle + and dots
    const email = currentUser.email || ''
    const local = email.split('@')[0] || ''
    const clean = local.split('+')[0].replace(/[._]/g, ' ')
    const nice = clean.split(' ').map(p => p.charAt(0).toUpperCase() + p.slice(1)).join(' ')
    setDisplayName(nice || currentUser.email)
  }, [currentUser])

  // Funkcija za pronalaženje imena knjige po ID-u
  const getBookTitle = (bookId) => {
    const book = books.find(b => b.id === bookId)
    return book ? book.title : `Knjiga #${bookId}`
  }

  // Funkcija za pronalaženje imena korisnika po ID-u
  const getUserName = (userId) => {
    // If this is the logged-in user, show their display name
    if (currentUser && currentUser.id === userId) {
      return displayName || currentUser.email
    }

    return mockUsers[userId] || `Korisnik #${userId}`
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: name === 'quantity' || name === 'book_id' || name === 'user_id' ? parseInt(value) : value
    }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    setSubmitting(true)
    setSubmitError(null)
    setSubmitSuccess(false)
    const token = localStorage.getItem('token')
    const headers = token ? { Authorization: `Bearer ${token}` } : {}
    // Ensure user is logged in and set user_id to current user's id
    if (!currentUser || !currentUser.id) {
      setSubmitError('Morate biti prijavljeni da biste kreirali narudžbinu')
      setSubmitting(false)
      return
    }

    const payload = { ...formData, user_id: currentUser.id }

    axios.post('http://localhost:8000/orders', payload, { headers })
      .then(r=> {
        setSubmitSuccess(true)
        setFormData({ user_id: 1, book_id: 1, quantity: 1 })
        setSubmitting(false)
        // Učitaj ponovo narudžbine
        setTimeout(() => {
          loadOrders()
          setSubmitSuccess(false)
        }, 2000)
      })
      .catch(err=> {
        console.error('Greška pri kreiranju narudžbine:', err)
        setSubmitError('Nije moguće kreirati narudžbinu')
        setSubmitting(false)
      })
  }

  return (
    <div style={{padding: 20, fontFamily: 'Arial, sans-serif'}}>
      <h1>📦 Narudžbine</h1>

      {/* Forma za novu narudžbinu */}
      <div style={{
        backgroundColor: '#ecf0f1',
        padding: 15,
        borderRadius: 5,
        marginBottom: 20
      }}>
        <h2 style={{marginTop: 0}}>Kreiraj novu narudžbinu</h2>
        <form onSubmit={handleSubmit}>
          {currentUser ? (
            <div style={{marginBottom: 10}}>
              <label style={{display: 'block', marginBottom: 5}}>Prijavljeni korisnik:</label>
              <div style={{padding: 8, width: '100%', maxWidth: 300, borderRadius: 3, border: '1px solid #ddd', background: '#fff'}}>
                {displayName || currentUser.email}
              </div>
            </div>
          ) : (
            <div style={{marginBottom: 10}}>
              <p>Morate se <a href="/auth/login">prijaviti</a> da biste kreirali narudžbinu.</p>
            </div>
          )}

          <div style={{marginBottom: 10}}>
            <label style={{display: 'block', marginBottom: 5}}>Knjiga:</label>
            <select
              name="book_id"
              value={formData.book_id}
              onChange={handleChange}
              style={{padding: 8, width: '100%', maxWidth: 300, borderRadius: 3, border: '1px solid #ddd'}}
            >
              {books.map(book => (
                <option key={book.id} value={book.id}>{book.title} ({book.price} дин)</option>
              ))}
            </select>
          </div>

          <div style={{marginBottom: 10}}>
            <label style={{display: 'block', marginBottom: 5}}>Količina:</label>
            <input
              type="number"
              name="quantity"
              value={formData.quantity}
              onChange={handleChange}
              min="1"
              style={{padding: 8, width: '100%', maxWidth: 300, borderRadius: 3, border: '1px solid #ddd'}}
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            style={{
              padding: '10px 20px',
              backgroundColor: '#27ae60',
              color: 'white',
              border: 'none',
              borderRadius: 3,
              cursor: submitting ? 'not-allowed' : 'pointer',
              opacity: submitting ? 0.6 : 1
            }}
          >
            {submitting ? 'Slanje...' : '📤 Kreiraj narudžbinu'}
          </button>
        </form>

        {submitError && <p style={{color: 'red', marginTop: 10}}>❌ {submitError}</p>}
        {submitSuccess && <p style={{color: 'green', marginTop: 10}}>✅ Narudžbina kreirana!</p>}
      </div>

      {/* Lista narudžbina */}
      <div>
        <h2>Sve narudžbine</h2>
        {loading && <p>Učitavanje...</p>}
        {error && <p style={{color: 'red'}}>{error}</p>}
        {!loading && orders.length === 0 ? (
          <p style={{color: '#666'}}>Nema narudžbina</p>
        ) : (
          <table style={{width: '100%', borderCollapse: 'collapse'}}>
            <thead>
              <tr style={{backgroundColor: '#f0f0f0'}}>
                <th style={{border: '1px solid #ddd', padding: 10, textAlign: 'left'}}>ID</th>
                <th style={{border: '1px solid #ddd', padding: 10, textAlign: 'left'}}>Korisnik</th>
                <th style={{border: '1px solid #ddd', padding: 10, textAlign: 'left'}}>Knjiga</th>
                <th style={{border: '1px solid #ddd', padding: 10, textAlign: 'left'}}>Količina</th>
                <th style={{border: '1px solid #ddd', padding: 10, textAlign: 'left'}}>Status</th>
              </tr>
            </thead>
            <tbody>
              {orders.map(order => (
                <tr key={order.id}>
                  <td style={{border: '1px solid #ddd', padding: 10}}>{order.id}</td>
                  <td style={{border: '1px solid #ddd', padding: 10}}>{getUserName(order.user_id)}</td>
                  <td style={{border: '1px solid #ddd', padding: 10}}>{getBookTitle(order.book_id)}</td>
                  <td style={{border: '1px solid #ddd', padding: 10}}>{order.quantity} kom.</td>
                  <td style={{border: '1px solid #ddd', padding: 10}}>
                    <span style={{
                      backgroundColor: order.status === 'created' ? '#27ae60' : '#95a5a6',
                      color: 'white',
                      padding: '5px 10px',
                      borderRadius: 3,
                      fontSize: 12
                    }}>
                      {order.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
