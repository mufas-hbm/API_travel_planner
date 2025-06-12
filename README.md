# Your Travel Planner Project

This project is aimed at developing a travel planning application with a focus on user-generated content, including destinations, travel plans, activities, and comments. The project leverages Django REST Framework for building a robust API, enabling user authentication, data validation, and more.

## Project Structure

- **Models**: Represents the core data structures.
- **Serializers**: Transforms complex data types into native Python datatypes.
- **Views**: Handles the HTTP requests and responses.
- **Filters**: Facilitates data retrieval through filtering.
- **Documentation**: Provides Swagger and ReDoc documentation for the API.

## Day 1: Create Models and Serializers

**Tasks:**
- Defined the following models:
  - `CustomUser`: Extended user model with additional fields.
  - `Destination`: Represents travel destinations.
  - `TravelPlan`: Represents travel plans created by users.
  - `Activity`: Represents activities associated with travel plans.
  - `Comment`: Represents user comments on destinations and travel plans.
  
- Created serializers for each model to facilitate data conversion:
  - `CustomUserSerializer`
  - `DestinationSerializer`
  - `TravelPlanSerializer`
  - `ActivitySerializer`
  - `CommentSerializer`

## Day 2: Add Validation and Sanitization

**Tasks:**
- Implemented validation rules for models to ensure data integrity:
  - Validated required fields and data formats.
  - Added custom validation methods where necessary.
- Implemented data sanitization to prevent invalid data from being stored in the database.

## Day 3: Authentication and Permission

**Tasks:**
- Set up user authentication using Token Authentication.
- Created views for user login and logout.
- Implemented custom permissions to restrict access:
  - `IsOwnerOrReadOnly`: Ensures users can only modify their own resources.
  - `IsAdminOrReadOnly`: Provides admin-level access to certain views.

## Day 4: Testing

**Tasks:**
- Created unit tests for models and serializers to ensure they function as expected.
- Tested authentication views and permission checks.
- Utilized Django's testing framework to write comprehensive test cases.

## Day 5: Swagger and ReDoc

**Tasks:**
- Integrated Swagger for automatic API documentation.
- Configured ReDoc for an alternative documentation interface.
- Ensured that each view has appropriate documentation, including request and response formats.

## Day 6: Filters

**Tasks:**
- Added filtering capabilities to the API using Django Filters.
- Implemented custom filters for each model to allow users to query data based on specific fields:
  - Enabled filtering for `name` and `country` in `Destination`.
  - Added relevant filters for other models as needed.

## Day 7: Finalization

**Tasks:**
- Reviewed and refined the codebase.
- Conducted a final round of testing to ensure everything is working as expected.
- Updated documentation to reflect any changes made during the finalization phase.
- Prepared for deployment or presentation of the project.
