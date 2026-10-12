## Technology stack
- Backend: Python and Django
- Database: PostgreSQL
- Frontend: Django templates, HTML, CSS, and JavaScript initially
- Version control: Git and GitHub
- Development environment: Windows with VS Code

Do not assume that all features must be implemented in the first version. Separate essential features from optional future enhancements.

## 1. Project overview
Explain the purpose of the website, the problem it solves, its objectives, its scope, and the expected outcomes.

## 2. Business requirements
Describe how a furniture business would use the system to display furniture, attract customers, process orders, manage inventory, and support customers.

Clearly distinguish an online furniture shop from an internal furniture management system.

## 3. User roles and permissions
Identify the different users, such as:
- Visitors
- Registered customers
- Administrators
- Inventory or store managers
- Sales staff

For each role, explain what the user can view, create, update, delete, or manage. Recommend the simplest suitable role structure for the first version.

## 4. Functional requirements
Describe the required features in detail, including:

- Homepage and navigation
- Furniture categories
- Product catalogue
- Product details, photographs, prices, sizes, materials, colours, and availability
- Search, filtering, sorting, and pagination
- Customer registration, login, logout, and profile management
- Shopping cart
- Checkout and order placement
- Delivery information and order tracking
- Payment methods, including cash on delivery and possible mobile money integration
- Inventory and stock management
- Product creation, editing, and archiving
- Order management
- Customer enquiries and contact information
- Administrator dashboard
- Sales and inventory reports

Classify each feature as essential for the minimum viable product (MVP), recommended for a later release, or optional. Explain why.

Do not assume that payment gateways, delivery integrations, or external services are already available.

## 5. Non-functional requirements
Specify usability, accessibility, responsiveness, performance, security, privacy, maintainability, reliability, and data integrity requirements.

Include practical security requirements for Django, such as CSRF protection, password hashing, authentication, authorization, input validation, secure configuration, and appropriate production settings.

## 6. UI/UX design
Describe the proposed visual identity, layout, navigation, typography, colour palette, responsive design, product cards, product detail pages, forms, buttons, and dashboard.

Recommend a professional furniture-industry aesthetic. Explain the main pages and what each should contain.

Do not generate images or code at this stage.

## 7. System architecture
Explain how Django, its apps, views, URL configurations, models, forms, templates, static files, and PostgreSQL will work together.

Recommend a maintainable Django project structure. Explain which responsibilities belong in each app and avoid unnecessary apps or complexity.

## 8. Database design
Identify the likely database entities and their relationships, including products, categories, product images, customers, addresses, carts, cart items, orders, order items, payments, and inventory where appropriate.

For each proposed entity, describe its purpose, important fields, primary keys, foreign keys, constraints, and relationships.

Distinguish essential MVP entities from optional entities. Do not generate database migrations yet.

## 9. URL and page plan
Propose the website's URL routes, including public pages, customer pages, authentication pages, and administrator pages.

Provide a table containing each route, its purpose, its access permissions, and its corresponding Django app.

## 10. Business rules
Define rules for product prices, stock availability, cart quantities, order totals, order status transitions, payment status, cancellation, refunds, and inventory updates.

Identify decisions that require confirmation instead of inventing business policies.

## 11. Security and testing
Recommend authentication and authorization practices, secure handling of customer data, protection against common web vulnerabilities, and testing strategies for models, views, forms, URLs, orders, and inventory.

## 12. Implementation roadmap
Provide a phased development plan, starting with requirements and project setup, then database design, catalogue, authentication, cart, orders, administration, testing, and deployment.

List dependencies between phases and define acceptance criteria for each phase.

## 13. Assumptions and open questions
List all assumptions and important unanswered questions, such as the target market, currency, delivery coverage, payment providers, guest checkout, returns policy, and whether the business already has furniture photographs and product data.

Do not silently make important business decisions.

## 14. Final deliverable
Produce a clear, detailed, beginner-friendly but professionally structured document titled "Furniture Website — Project Specification".

Use Markdown headings, tables, numbered lists, and checklists where appropriate.

Make the document specific to