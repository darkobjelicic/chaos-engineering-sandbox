import http from "k6/http";
import { check, group, sleep } from "k6";

// Stress test: ramps beyond normal capacity to find breaking point
// Override: make stress VUS=50 DURATION=10m
const MAX_VUS  = parseInt(__ENV.VUS      || "50");
const DURATION = __ENV.DURATION          || "10m";

export const options = {
  stages: [
    { duration: "2m",     target: Math.floor(MAX_VUS * 0.5) },  // warm up to 50%
    { duration: "3m",     target: MAX_VUS },                     // ramp to full load
    { duration: DURATION, target: MAX_VUS },                     // hold at max
    { duration: "2m",     target: 0 },                           // ramp down
  ],
  thresholds: {
    // Relaxed thresholds — stress test expects degradation
    http_req_failed:                        ["rate<0.20"],
    http_req_duration:                      ["p(95)<3000"],
    "http_req_duration{group:::browse}":    ["p(95)<2000"],
    "http_req_duration{group:::order}":     ["p(95)<5000"],
  },
};

const BASE_URL = __ENV.BASE_URL || "http://api.bookstore.local";

export function setup() {
  const email = `stress-${Date.now()}@test.local`;
  const reg = http.post(
    `${BASE_URL}/auth/register`,
    JSON.stringify({ email, password: "stress123" }),
    { headers: { "Content-Type": "application/json" } }
  );
  if (reg.status !== 200) {
    console.warn(`Registration failed: ${reg.status}`);
    return { token: null };
  }
  return { token: reg.json("access_token") };
}

export default function (data) {
  if (Math.random() < 0.6) {
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

  // No sleep — maximum throughput under stress
}
