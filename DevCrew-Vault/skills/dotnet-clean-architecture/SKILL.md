---
name: dotnet-clean-architecture
description: >
  Scaffolds and implements Clean Architecture in .NET 8+ projects. Use when
  starting a new .NET solution, refactoring a layered mess, building a
  Domain-Driven Design (DDD) project, or developing an enterprise application.
  Invoke when you need strict layer isolation, testability, and long-term
  maintainability. Do not use for simple CRUD APIs, throwaway prototypes, or
  single-file scripts.
license: MIT
compatibility:
  - claude-3-5-sonnet
  - gpt-4o
metadata:
  origin: authored
  review_status: needs-human-review
allowed-tools:
  - read_file
  - write_file
  - run_command
---

# .NET Clean Architecture Scaffolder

## When to Use / When Not to Use

### Use When
- Starting a **new .NET 8+ solution** that will grow beyond a single service.
- **Refactoring** an existing "big ball of mud" or classic N-tier architecture.
- Building a **DDD / domain-rich** application where business rules deserve first-class status.
- Developing an **enterprise application** with multiple teams, bounded contexts, or complex workflows.
- The team needs strict **unit testability** at the domain and application layers without spinning up a database.

### Do NOT Use When
- The project is a **simple CRUD API** with no real business logic (use minimal API or a lightweight MVC project instead).
- You are building a **prototype or spike** — the overhead of Clean Architecture will slow you down.
- The deliverable is a **CLI script or small utility** — use a single console project.
- The team is very small and unfamiliar with the pattern — training cost may outweigh benefits for tiny scopes.

---

## Procedure

### 1. Create the Solution Structure

```
dotnet new sln -n MyApp
mkdir src tests

# Domain layer — zero external dependencies
dotnet new classlib -n MyApp.Domain -o src/MyApp.Domain --framework net8.0

# Application layer — depends only on Domain
dotnet new classlib -n MyApp.Application -o src/MyApp.Application --framework net8.0

# Infrastructure layer — depends on Application + Domain
dotnet new classlib -n MyApp.Infrastructure -o src/MyApp.Infrastructure --framework net8.0

# Presentation layer (Web API)
dotnet new webapi -n MyApp.WebApi -o src/MyApp.WebApi --framework net8.0

# Test projects
dotnet new xunit -n MyApp.Domain.Tests -o tests/MyApp.Domain.Tests --framework net8.0
dotnet new xunit -n MyApp.Application.Tests -o tests/MyApp.Application.Tests --framework net8.0

# Add all to solution
dotnet sln add src/MyApp.Domain/MyApp.Domain.csproj
dotnet sln add src/MyApp.Application/MyApp.Application.csproj
dotnet sln add src/MyApp.Infrastructure/MyApp.Infrastructure.csproj
dotnet sln add src/MyApp.WebApi/MyApp.WebApi.csproj
dotnet sln add tests/MyApp.Domain.Tests/MyApp.Domain.Tests.csproj
dotnet sln add tests/MyApp.Application.Tests/MyApp.Application.Tests.csproj
```

### 2. Establish Project References (Dependency Rule)

The **Dependency Rule**: source code dependencies must point **inward** only.

```
dotnet add src/MyApp.Application/MyApp.Application.csproj reference src/MyApp.Domain/MyApp.Domain.csproj
dotnet add src/MyApp.Infrastructure/MyApp.Infrastructure.csproj reference src/MyApp.Application/MyApp.Application.csproj
dotnet add src/MyApp.WebApi/MyApp.WebApi.csproj reference src/MyApp.Application/MyApp.Application.csproj
dotnet add src/MyApp.WebApi/MyApp.WebApi.csproj reference src/MyApp.Infrastructure/MyApp.Infrastructure.csproj
dotnet add tests/MyApp.Application.Tests/MyApp.Application.Tests.csproj reference src/MyApp.Application/MyApp.Application.csproj
dotnet add tests/MyApp.Application.Tests/MyApp.Application.Tests.csproj reference src/MyApp.Domain/MyApp.Domain.csproj
```

> **Rule:** Domain NEVER references Application or Infrastructure. Application NEVER references Infrastructure.

### 3. Add NuGet Packages Per Layer

**Application layer:**
```
dotnet add src/MyApp.Application package MediatR
dotnet add src/MyApp.Application package FluentValidation
dotnet add src/MyApp.Application package FluentValidation.DependencyInjectionExtensions
dotnet add src/MyApp.Application package Microsoft.Extensions.DependencyInjection.Abstractions
```

**Infrastructure layer:**
```
dotnet add src/MyApp.Infrastructure package Microsoft.EntityFrameworkCore
dotnet add src/MyApp.Infrastructure package Microsoft.EntityFrameworkCore.SqlServer
dotnet add src/MyApp.Infrastructure package Microsoft.EntityFrameworkCore.Tools
```

**WebApi layer:**
```
dotnet add src/MyApp.WebApi package Microsoft.AspNetCore.OpenApi
dotnet add src/MyApp.WebApi package Swashbuckle.AspNetCore
```

### 4. Define the Domain Layer

Create clean, framework-free domain entities with private setters, aggregate roots, and domain events.

```csharp
// src/MyApp.Domain/Entities/Order.cs
namespace MyApp.Domain.Entities;

public class Order : AggregateRoot
{
    private readonly List<OrderItem> _items = new();

    public Guid CustomerId { get; private set; }
    public OrderStatus Status { get; private set; }
    public IReadOnlyList<OrderItem> Items => _items.AsReadOnly();

    private Order() { } // EF Core

    public static Order Create(Guid customerId)
    {
        ArgumentNullException.ThrowIfNull(customerId);
        var order = new Order
        {
            Id = Guid.NewGuid(),
            CustomerId = customerId,
            Status = OrderStatus.Pending
        };
        order.AddDomainEvent(new OrderCreatedEvent(order.Id));
        return order;
    }

    public void AddItem(Guid productId, int quantity, decimal unitPrice)
    {
        if (Status != OrderStatus.Pending)
            throw new DomainException("Cannot modify a non-pending order.");
        _items.Add(new OrderItem(productId, quantity, unitPrice));
    }
}
```

### 5. Define Application Layer — CQRS with MediatR

Separate **Commands** (write) from **Queries** (read). Each gets its own request + handler.

```csharp
// src/MyApp.Application/Orders/Commands/CreateOrder/CreateOrderCommand.cs
namespace MyApp.Application.Orders.Commands.CreateOrder;

public sealed record CreateOrderCommand(Guid CustomerId) : IRequest<Guid>;
```

```csharp
// src/MyApp.Application/Orders/Commands/CreateOrder/CreateOrderCommandHandler.cs
namespace MyApp.Application.Orders.Commands.CreateOrder;

public sealed class CreateOrderCommandHandler : IRequestHandler<CreateOrderCommand, Guid>
{
    private readonly IOrderRepository _orderRepository;
    private readonly IUnitOfWork _unitOfWork;

    public CreateOrderCommandHandler(IOrderRepository orderRepository, IUnitOfWork unitOfWork)
    {
        _orderRepository = orderRepository;
        _unitOfWork = unitOfWork;
    }

    public async Task<Guid> Handle(CreateOrderCommand request, CancellationToken cancellationToken)
    {
        var order = Order.Create(request.CustomerId);
        await _orderRepository.AddAsync(order, cancellationToken);
        await _unitOfWork.SaveChangesAsync(cancellationToken);
        return order.Id;
    }
}
```

### 6. Add FluentValidation

```csharp
// src/MyApp.Application/Orders/Commands/CreateOrder/CreateOrderCommandValidator.cs
namespace MyApp.Application.Orders.Commands.CreateOrder;

public sealed class CreateOrderCommandValidator : AbstractValidator<CreateOrderCommand>
{
    public CreateOrderCommandValidator()
    {
        RuleFor(x => x.CustomerId)
            .NotEmpty().WithMessage("CustomerId is required.");
    }
}
```

Register a MediatR validation pipeline behavior in `ApplicationServiceExtensions`:

```csharp
services.AddValidatorsFromAssembly(Assembly.GetExecutingAssembly());
services.AddTransient(typeof(IPipelineBehavior<,>), typeof(ValidationPipelineBehavior<,>));
```

### 7. Infrastructure — EF Core DbContext

```csharp
// src/MyApp.Infrastructure/Persistence/AppDbContext.cs
namespace MyApp.Infrastructure.Persistence;

public class AppDbContext : DbContext, IUnitOfWork
{
    public DbSet<Order> Orders => Set<Order>();

    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.ApplyConfigurationsFromAssembly(typeof(AppDbContext).Assembly);
    }

    public async Task SaveChangesAsync(CancellationToken cancellationToken = default)
        => await base.SaveChangesAsync(cancellationToken);
}
```

### 8. Register Services in WebApi

```csharp
// src/MyApp.WebApi/Program.cs
builder.Services.AddApplicationServices();   // from Application layer extension
builder.Services.AddInfrastructureServices(builder.Configuration); // from Infrastructure layer extension
```

### 9. Write Unit Tests

Test domain and application independently — no DB, no HTTP:

```csharp
[Fact]
public void Order_Create_ShouldRaiseDomainEvent()
{
    var order = Order.Create(Guid.NewGuid());
    Assert.Contains(order.DomainEvents, e => e is OrderCreatedEvent);
}
```

---

## Checklist

- [ ] **Domain** has zero references to EF Core, MediatR, or any framework
- [ ] **Application** only references Domain (no Infrastructure leaking in)
- [ ] **Infrastructure** implements interfaces defined in Application/Domain
- [ ] CQRS: Commands and Queries are in separate files/folders
- [ ] Every command has a corresponding `Validator`
- [ ] `IUnitOfWork` is defined in Application, implemented in Infrastructure
- [ ] `IRepository<T>` interfaces live in Domain or Application, not Infrastructure
- [ ] MediatR pipeline behaviors registered (Validation, Logging)
- [ ] No `static` state or service locator anti-patterns
- [ ] Domain entities cannot be created in invalid state (private setters, factory methods)
- [ ] Unit tests cover domain entity invariants
- [ ] Integration tests use an in-memory or SQLite DB, not production DB

---

## Common Pitfalls

| Pitfall | Description | Fix |
|---|---|---|
| **Domain bleeding** | Domain entity imports EF Core attributes | Move mapping to `IEntityTypeConfiguration<T>` in Infrastructure |
| **Skipping Application layer** | Controller calls repository directly | Always route through MediatR command/query |
| **Fat handlers** | Handler does validation + business logic + persistence | Extract domain logic to entity methods; use pipeline behaviors |
| **Shared DbContext in tests** | Tests share a single DbContext causing interference | Use `DbContextOptions` with unique in-memory DB names per test |
| **Over-engineering** | Using DDD aggregates for a 3-table app | Evaluate complexity; prefer simple CRUD if domain is trivial |
| **Anemic domain model** | Entities are just data bags, all logic in services | Move invariants and behavior into the entity itself |

---

## Worked Example: `CreateOrderCommand` End-to-End

**Goal:** Accept a POST request, validate it, create an `Order` aggregate, persist it.

1. **Controller** receives `POST /api/orders` with `{ "customerId": "..." }`
2. **Controller** sends `new CreateOrderCommand(customerId)` via `ISender.Send(...)`
3. **ValidationPipelineBehavior** runs `CreateOrderCommandValidator` — rejects if invalid
4. **CreateOrderCommandHandler** calls `Order.Create(customerId)` → domain event raised
5. **Handler** calls `_orderRepository.AddAsync(order)` and `_unitOfWork.SaveChangesAsync()`
6. EF Core **AppDbContext** persists the aggregate; domain event published post-save
7. Controller returns `201 Created` with the new order ID

See `references/deep-dive.md` for detailed reference material.
