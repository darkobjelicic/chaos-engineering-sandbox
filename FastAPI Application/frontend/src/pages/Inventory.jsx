import React, { useEffect, useState } from 'react'
import axios from 'axios'

export default function Inventory(){
  const [inventory, setInventory] = useState([])
  const [books, setBooks] = useState([])
  const [loading, setLoading] = useState(true)
  const [booksLoading, setBooksLoading] = useState(true)
  const [error, setError] = useState(null)

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

  // Učitaj zalihе
  useEffect(()=>{
    axios.get('http://localhost:8000/inventory')
      .then(r=> {
        setInventory(r.data || [])
        setLoading(false)
      })
      .catch(err=> {
        console.error('Greška pri učitavanju zaliha:', err)
        setError('Nije moguće učitati zalihе')
        setLoading(false)
      })
  },[])

  // Funkcija za pronalaženje imena knjige po ID-u
  const getBookTitle = (bookId) => {
    const book = books.find(b => b.id === bookId)
    return book ? book.title : `Knjiga #${bookId}`
  }

  // Funkcija za pronalaženje cene knjige po ID-u
  const getBookPrice = (bookId) => {
    const book = books.find(b => b.id === bookId)
    return book ? book.price : 'N/A'
  }

  return (
    <div style={{padding: 20, fontFamily: 'Arial, sans-serif'}}>
      <h1>📦 Stanje zaliha</h1>
      {loading && <p>Učitavanje...</p>}
      {error && <p style={{color: 'red'}}>{error}</p>}
      {!loading && inventory.length === 0 ? (
        <p>Nema podataka o zalihama</p>
      ) : (
        <table style={{width: '100%', borderCollapse: 'collapse'}}>
          <thead>
            <tr style={{backgroundColor: '#f0f0f0'}}>
              <th style={{border: '1px solid #ddd', padding: 10, textAlign: 'left'}}>Knjiga</th>
              <th style={{border: '1px solid #ddd', padding: 10, textAlign: 'left'}}>Cena</th>
              <th style={{border: '1px solid #ddd', padding: 10, textAlign: 'left'}}>Količina</th>
            </tr>
          </thead>
          <tbody>
            {inventory.map(inv => (
              <tr key={inv.id}>
                <td style={{border: '1px solid #ddd', padding: 10}}>{getBookTitle(inv.book_id)}</td>
                <td style={{border: '1px solid #ddd', padding: 10}}>{getBookPrice(inv.book_id)} дин</td>
                <td style={{border: '1px solid #ddd', padding: 10}}>
                  <strong style={{color: inv.quantity > 10 ? '#27ae60' : '#e74c3c'}}>
                    {inv.quantity} kom.
                  </strong>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
