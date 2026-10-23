"""Held-out test questions: NEW questions that were not used to design or tune the prompt.
Use them to check whether a prompt improvement is real. (question, correct SQL, difficulty)"""

J = ("FROM orders o JOIN customers c ON o.customer_id = c.id JOIN order_items oi ON oi.order_id = o.id "
     "JOIN products p ON p.id = oi.product_id")

TESTS_HELDOUT = [
    ("How many customers are there in Delhi?", "SELECT COUNT(*) FROM customers WHERE city = 'Delhi'", "easy"),
    ("List the names of products in the Stationery category", "SELECT name FROM products WHERE category = 'Stationery'", "easy"),
    ("How many orders were placed in 2026?", "SELECT COUNT(*) FROM orders WHERE strftime('%Y', order_date) = '2026'", "medium"),
    ("How many products costing more than 1000 are there in each category?",
     "SELECT category, COUNT(*) FROM products WHERE price > 1000 GROUP BY category", "medium"),
    ("What is the total revenue (quantity multiplied by price) for each city?",
     f"SELECT c.city, SUM(oi.quantity * p.price) {J} GROUP BY c.city", "hard"),
    ("List the customers from Pune who bought a Backpack",
     f"SELECT DISTINCT c.name {J} WHERE c.city = 'Pune' AND p.name = 'Backpack'", "hard"),
    ("What is the highest order value, where an order's value is the sum of quantity multiplied by price of its items?",
     "SELECT MAX(v) FROM (SELECT SUM(oi.quantity * p.price) v FROM order_items oi JOIN products p ON p.id = oi.product_id GROUP BY oi.order_id)", "hard"),
    ("How many customers bought both a Laptop and a Phone?",
     f"SELECT COUNT(*) FROM (SELECT c.id {J} WHERE p.name IN ('Laptop', 'Phone') GROUP BY c.id HAVING COUNT(DISTINCT p.name) = 2)", "hard"),
    ("What is the cheapest product in each category?",
     "SELECT category, name FROM products p WHERE price = (SELECT MIN(price) FROM products WHERE category = p.category)", "hard"),
    ("What is the average order value for orders placed in 2025, where an order's value is the sum of quantity multiplied by price of its items?",
     "SELECT AVG(v) FROM (SELECT SUM(oi.quantity * p.price) v FROM orders o JOIN order_items oi ON oi.order_id = o.id "
     "JOIN products p ON p.id = oi.product_id WHERE strftime('%Y', o.order_date) = '2025' GROUP BY o.id)", "hard"),
    ("Which products have not been bought by any customer from Delhi?",
     "SELECT name FROM products WHERE id NOT IN (SELECT oi.product_id FROM order_items oi JOIN orders o ON oi.order_id = o.id "
     "JOIN customers c ON o.customer_id = c.id WHERE c.city = 'Delhi')", "hard"),
    ("What is the total revenue (quantity multiplied by price) for each year?",
     f"SELECT strftime('%Y', o.order_date), SUM(oi.quantity * p.price) {J} GROUP BY 1", "hard"),
]
