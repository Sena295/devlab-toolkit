-- Consultas analíticas para o banco gerado por `python -m datagen.generate out/`.
-- Rode com:  sqlite3 out/loja.db < sql/analytics.sql

-- 1. Receita por mês
SELECT substr(ordered_at, 1, 7) AS mes, ROUND(SUM(total), 2) AS receita, COUNT(*) AS pedidos
FROM orders
GROUP BY mes
ORDER BY mes;

-- 2. Top 5 clientes por gasto
SELECT c.name, c.city, ROUND(SUM(o.total), 2) AS gasto
FROM orders o
JOIN customers c ON c.id = o.customer_id
GROUP BY c.id
ORDER BY gasto DESC
LIMIT 5;

-- 3. Ticket médio por cidade
SELECT c.city, ROUND(AVG(o.total), 2) AS ticket_medio, COUNT(*) AS pedidos
FROM orders o
JOIN customers c ON c.id = o.customer_id
GROUP BY c.city
ORDER BY ticket_medio DESC;

-- 4. Ranking de produtos com participação na receita (window function)
SELECT product,
       ROUND(SUM(total), 2) AS receita,
       ROUND(100.0 * SUM(total) / SUM(SUM(total)) OVER (), 1) AS pct,
       RANK() OVER (ORDER BY SUM(total) DESC) AS posicao
FROM orders
GROUP BY product;

-- 5. Receita acumulada mês a mês
WITH mensal AS (
    SELECT substr(ordered_at, 1, 7) AS mes, SUM(total) AS receita FROM orders GROUP BY mes
)
SELECT mes, ROUND(receita, 2) AS receita,
       ROUND(SUM(receita) OVER (ORDER BY mes), 2) AS acumulado
FROM mensal;

-- 6. Clientes sem nenhum pedido
SELECT c.id, c.name
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id
WHERE o.id IS NULL;
