import http from "k6/http";
import { check, group, sleep } from "k6";

// ── Stages ────────────────────────────────────────────────────────────────────
// 0:00 – 2:00   ramp up to steady state
// 2:00 – 10:00  baseline (8 min) — observe normal behaviour before chaos
// 10:00 – 25:00 chaos window (15 min) — inject failures here
// 25:00 – 27:00 ramp down
export const options = {
  stages: [
    { duration: "2m", target: 20 },
    { duration: "8m", target: 20 },
    { duration: "15m", target: 20 },
    { duration: "2m", target: 0 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(95)<1000"],
    "http_req_duration{group:::browse}": ["p(95)<500"],
    "http_req_duration{group:::order}": ["p(95)<1500"],
  },
};

const BASE_URL = __ENV.BASE_URL || "http://api.bookstore.local";

export function setup() {
  const email = `loadtest-${Date.now()}@test.local`;
  const reg = http.post(
    `${BASE_URL}/auth/register`,
    JSON.stringify({ email, password: "loadtest123" }),
    { headers: { "Content-Type": "application/json" } }
  );
  if (reg.status !== 200) {
    console.warn(`Registration failed: ${reg.status}`);
    return { token: null };
  }
  return { token: reg.json("access_token") };
}

export default function (data) {
  if (Math.random() < 0.7) {
    group("browse", () => {
      const books = http.get(`${BASE_URL}/books`);
      check(books, { "books 200": (r) => r.status === 200 });

      const book = http.get(`${BASE_URL}/books/${Math.ceil(Math.random() * 4)}`);
      check(book, { "book 200": (r) => r.status === 200 });

      const inv = http.get(`${BASE_URL}/inventory`);
      check(inv, { "inventory 200": (r) => r.status === 200 });
    });
  } else {
    group("order", () => {
      if (!data.token) return;
      const res = http.post(
        `${BASE_URL}/orders`,
        JSON.stringify({ book_id: Math.ceil(Math.random() * 4), quantity: 1 }),
        {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${data.token}`,
          },
        }
      );
      check(res, { "order 200": (r) => r.status === 200 });
    });
  }

  sleep(1);
}
