import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 3,
  duration: "1m",
  thresholds: {
    http_req_failed: ["rate<0.01"],       // error rate < 1%
    http_req_duration: ["p(95)<1000"],    // p95 < 1000ms (smoke — just checking things work)
  },
};

const BASE_URL = __ENV.BASE_URL || "http://api.bookstore.local";

export default function () {
  // Health check
  const health = http.get(`${BASE_URL}/health`);
  check(health, { "health ok": (r) => r.status === 200 });

  // List books
  const books = http.get(`${BASE_URL}/books`);
  check(books, {
    "books ok": (r) => r.status === 200,
    "books not empty": (r) => JSON.parse(r.body).length > 0,
  });

  // Single book
  const book = http.get(`${BASE_URL}/books/1`);
  check(book, { "book found": (r) => r.status === 200 });

  // Inventory
  const inventory = http.get(`${BASE_URL}/inventory`);
  check(inventory, { "inventory ok": (r) => r.status === 200 });

  sleep(1);
}
