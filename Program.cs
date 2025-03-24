using Microsoft.EntityFrameworkCore;
using SmartStay.Data;
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.OpenApi.Models;

var builder = WebApplication.CreateBuilder(args);

// ✅ Get the connection string and ensure TrustServerCertificate is enabled
var connectionString = builder.Configuration.GetConnectionString("DefaultConnection") 
    + ";TrustServerCertificate=True";

// ✅ Register required services
builder.Services.AddControllersWithViews(); // Supports Views & TempData
builder.Services.AddSession(); // Enables Session for TempData
builder.Services.AddDbContext<ApplicationDbContext>(options =>
    options.UseSqlServer(connectionString));

// ✅ Add API & Swagger support
builder.Services.AddControllers(); // API Controllers
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new OpenApiInfo
    {
        Title = "SmartStay API",
        Version = "v1"
    });
});

var app = builder.Build();

// ✅ Configure middleware
if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Home/Error");
    app.UseHsts();
}
else
{
    app.UseDeveloperExceptionPage();
    app.UseSwagger();
    app.UseSwaggerUI(c =>
    {
        c.SwaggerEndpoint("/swagger/v1/swagger.json", "SmartStay API v1");
        c.RoutePrefix = "swagger"; // Swagger UI available at /swagger
    });
}

app.UseHttpsRedirection();
app.UseStaticFiles(); // ✅ Required for serving static assets like CSS/JS
app.UseRouting();
app.UseSession(); // ✅ Enables TempData
app.UseAuthorization();

// ✅ Set up routing for both MVC & API controllers
app.MapControllers(); // API routes
app.MapControllerRoute(
    name: "default",
    pattern: "{controller=Home}/{action=Index}/{id?}"); // Default MVC route

app.Run();
