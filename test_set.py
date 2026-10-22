"""Test set for the SAMPLE shop database: (question, correct SQL, difficulty).
32 questions are ready. ADD 10-18 MORE of your own to reach 40-50 (see the end of the file).

Tips for writing good test questions:
- The answer must be unique: avoid ties (e.g. two cities with the same count) for "top 1 / most" questions.
- Say clearly what you want, e.g. "revenue (quantity multiplied by price)".
- The correct SQL is written by YOU and checked by running it. Do not copy it from the LLM.
"""

REV = "SUM(oi.quantity * p.price)"

TESTS = [
    # ---------------- EASY ----------------
    ("How many customers are there?", "SELECT COUNT(*) FROM customers", "easy"),
    ("How many products are there?", "SELECT COUNT(*) FROM products", "easy"),
    ("What is the most expensive product?", "SELECT name FROM products ORDER BY price DESC LIMIT 1", "easy"),
    ("What is the cheapest product?", "SELECT name FROM products ORDER BY price ASC LIMIT 1", "easy"),
    ("List all products in the Electronics category", "SELECT name FROM products WHERE category = 'Electronics'", "easy"),
    ("List all customers from Pune", "SELECT name FROM customers WHERE city = 'Pune'", "easy"),
    ("How many orders are there in total?", "SELECT COUNT(*) FROM orders", "easy"),
    ("Which products cost more than 10000?", "SELECT name FROM products WHERE price > 10000", "easy"),
    ("How many products are in the Furniture category?", "SELECT COUNT(*) FROM products WHERE category = 'Furniture'", "easy"),
    ("List all the different cities where customers live", "SELECT DISTINCT city FROM customers", "easy"),

    # ---------------- MEDIUM ----------------
    ("Which cities have more than 6 customers?",
     "SELECT city FROM customers GROUP BY city HAVING COUNT(*) > 6", "medium"),
    ("How many customers are there in each city?",
     "SELECT city, COUNT(*) FROM customers GROUP BY city", "medium"),
    ("Show the average price of products in each category",
     "SELECT category, AVG(price) FROM products GROUP BY category", "medium"),
    ("How many products are there in each category?",
     "SELECT category, COUNT(*) FROM products GROUP BY category", "medium"),
    ("How many orders were placed in 2025?",
     "SELECT COUNT(*) FROM orders WHERE strftime('%Y', order_date) = '2025'", "medium"),
    ("How many orders were placed in each year?",
     "SELECT strftime('%Y', order_date), COUNT(*) FROM orders GROUP BY 1", "medium"),
    ("How many orders were placed in March (in any year)?",
     "SELECT COUNT(*) FROM orders WHERE strftime('%m', order_date) = '03'", "medium"),
    ("What is the total quantity of all items sold?", "SELECT SUM(quantity) FROM order_items", "medium"),
    ("What is the average product price?", "SELECT AVG(price) FROM products", "medium"),
    ("List the 3 cheapest products with their prices",
     "SELECT name, price FROM products ORDER BY price ASC LIMIT 3", "medium"),
    ("How many orders did customer 5 place?", "SELECT COUNT(*) FROM orders WHERE customer_id = 5", "medium"),
    ("Which category has the highest average product price?",
     "SELECT category FROM products GROUP BY category ORDER BY AVG(price) DESC LIMIT 1", "medium"),

    # ---------------- HARD (joins) ----------------
    ("Top 3 products by total quantity sold",
     "SELECT p.name FROM order_items oi JOIN products p ON oi.product_id = p.id "
     "GROUP BY p.name ORDER BY SUM(oi.quantity) DESC LIMIT 3", "hard"),
    ("What is the total revenue (quantity multiplied by price) for each product category?",
     f"SELECT p.category, {REV} FROM order_items oi JOIN products p ON oi.product_id = p.id GROUP BY p.category", "hard"),
    ("Which customer has placed the most orders?",
     "SELECT c.name FROM orders o JOIN customers c ON o.customer_id = c.id "
     "GROUP BY c.id ORDER BY COUNT(*) DESC LIMIT 1", "hard"),
    ("Which city has the highest total sales (quantity multiplied by price)?",
     f"SELECT c.city FROM orders o JOIN customers c ON o.customer_id = c.id "
     f"JOIN order_items oi ON oi.order_id = o.id JOIN products p ON p.id = oi.product_id "
     f"GROUP BY c.city ORDER BY {REV} DESC LIMIT 1", "hard"),
    ("Which customers bought a Laptop?",
     "SELECT DISTINCT c.name FROM customers c JOIN orders o ON o.customer_id = c.id "
     "JOIN order_items oi ON oi.order_id = o.id JOIN products p ON p.id = oi.product_id "
     "WHERE p.name = 'Laptop'", "hard"),
    ("What is the total quantity sold for each product category?",
     "SELECT p.category, SUM(oi.quantity) FROM order_items oi JOIN products p ON oi.product_id = p.id "
     "GROUP BY p.category", "hard"),
    ("Which customers have placed more than 8 orders?",
     "SELECT c.name FROM customers c JOIN orders o ON o.customer_id = c.id "
     "GROUP BY c.id HAVING COUNT(*) > 8", "hard"),
    ("What is the total revenue (quantity multiplied by price) in 2025?",
     f"SELECT {REV} FROM orders o JOIN order_items oi ON oi.order_id = o.id "
     f"JOIN products p ON p.id = oi.product_id WHERE strftime('%Y', o.order_date) = '2025'", "hard"),
    ("Which product appears in the most distinct orders?",
     "SELECT p.name FROM order_items oi JOIN products p ON oi.product_id = p.id "
     "GROUP BY p.name ORDER BY COUNT(DISTINCT oi.order_id) DESC LIMIT 1", "hard"),
    ("Which product category has the highest total revenue (quantity multiplied by price)?",
     f"SELECT p.category FROM order_items oi JOIN products p ON oi.product_id = p.id "
     f"GROUP BY p.category ORDER BY {REV} DESC LIMIT 1", "hard"),

    # ---------------- EXTRA TRICKY (subqueries, months, per-category, multi-join) ----------------
    ('Which customer spent the most in total (quantity multiplied by price)?',
     'SELECT c.name FROM orders o JOIN customers c ON o.customer_id=c.id JOIN order_items oi ON oi.order_id=o.id JOIN products p ON p.id=oi.product_id GROUP BY c.id ORDER BY SUM(oi.quantity*p.price) DESC LIMIT 1', 'hard'),
    ('Which three customers spent the most in total (quantity multiplied by price)?',
     'SELECT c.name FROM orders o JOIN customers c ON o.customer_id=c.id JOIN order_items oi ON oi.order_id=o.id JOIN products p ON p.id=oi.product_id GROUP BY c.id ORDER BY SUM(oi.quantity*p.price) DESC LIMIT 3', 'hard'),
    ('What is the total revenue (quantity multiplied by price) for each month of 2026?',
     "SELECT strftime('%m', o.order_date), SUM(oi.quantity*p.price) FROM orders o JOIN customers c ON o.customer_id=c.id JOIN order_items oi ON oi.order_id=o.id JOIN products p ON p.id=oi.product_id WHERE strftime('%Y', o.order_date)='2026' GROUP BY 1", 'hard'),
    ("What is the average order value, where an order's value is the sum of quantity multiplied by price of its items?",
     'SELECT AVG(v) FROM (SELECT SUM(oi.quantity*p.price) v FROM order_items oi JOIN products p ON p.id=oi.product_id GROUP BY oi.order_id)', 'hard'),
    ('How many different customers bought a product from the Furniture category?',
     "SELECT COUNT(DISTINCT c.id) FROM orders o JOIN customers c ON o.customer_id=c.id JOIN order_items oi ON oi.order_id=o.id JOIN products p ON p.id=oi.product_id WHERE p.category='Furniture'", 'hard'),
    ('List the customers from Mumbai who bought a Phone',
     "SELECT DISTINCT c.name FROM orders o JOIN customers c ON o.customer_id=c.id JOIN order_items oi ON oi.order_id=o.id JOIN products p ON p.id=oi.product_id WHERE c.city='Mumbai' AND p.name='Phone'", 'hard'),
    ('How many orders contained more than one product?',
     'SELECT COUNT(*) FROM (SELECT order_id FROM order_items GROUP BY order_id HAVING COUNT(*)>1)', 'hard'),
    ('What is the most expensive product in each category?',
     'SELECT category, name FROM products p WHERE price=(SELECT MAX(price) FROM products WHERE category=p.category)', 'hard'),
    ('How many customers placed orders in both 2025 and 2026?',
     "SELECT COUNT(*) FROM (SELECT customer_id FROM orders GROUP BY customer_id HAVING COUNT(DISTINCT strftime('%Y', order_date))=2)", 'hard'),
    ('What is the total quantity of Electronics products sold to customers in Mumbai?',
     "SELECT SUM(oi.quantity) FROM orders o JOIN customers c ON o.customer_id=c.id JOIN order_items oi ON oi.order_id=o.id JOIN products p ON p.id=oi.product_id WHERE p.category='Electronics' AND c.city='Mumbai'", 'hard'),
    ('Which customers bought products from all four categories?',
     'SELECT c.name FROM orders o JOIN customers c ON o.customer_id=c.id JOIN order_items oi ON oi.order_id=o.id JOIN products p ON p.id=oi.product_id GROUP BY c.id HAVING COUNT(DISTINCT p.category)=4', 'hard'),
    ('Which products have been ordered by more than 20 different customers?',
     'SELECT p.name FROM orders o JOIN customers c ON o.customer_id=c.id JOIN order_items oi ON oi.order_id=o.id JOIN products p ON p.id=oi.product_id GROUP BY p.name HAVING COUNT(DISTINCT c.id)>20', 'hard'),

    # ---------------- ADD YOUR OWN QUESTIONS BELOW (aim for 40-50 in total) ----------------
    # ("Your question here?", "SELECT ... ", "easy/medium/hard"),
]