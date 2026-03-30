import re
from marshmallow import Schema, ValidationError, fields, validate, validates
from app.models import Category

HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


class CategorySchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=50),
    )
    color = fields.Str(
        allow_none=True,
        validate=validate.Regexp(
            HEX_COLOR_PATTERN,
            error="Color must be a valid hex format like #FF5733.",
        ),
    )

    @validates("name")
    def validate_unique_name(self, value, **kwargs):
        existing_category = Category.query.filter_by(name=value).first()
        if existing_category:
            raise ValidationError("Category with this name already exists.")


class TaskSchema(Schema):
    id = fields.Int(dump_only=True)
    title = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=100),
    )
    description = fields.Str(
        allow_none=True,
        validate=validate.Length(max=500),
    )
    completed = fields.Bool(load_default=False)
    due_date = fields.DateTime(allow_none=True)
    category_id = fields.Int(allow_none=True)

    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    @validates("category_id")
    def validate_category_exists(self, value, **kwargs):
        if value is None:
            return

        category = Category.query.get(value)
        if category is None:
            raise ValidationError("Category does not exist.")


class TaskUpdateSchema(Schema):
    title = fields.Str(
        validate=validate.Length(min=1, max=100),
    )
    description = fields.Str(
        allow_none=True,
        validate=validate.Length(max=500),
    )
    completed = fields.Bool()
    due_date = fields.DateTime(allow_none=True)
    category_id = fields.Int(allow_none=True)

    @validates("category_id")
    def validate_category_exists(self, value, **kwargs):
        if value is None:
            return

        category = Category.query.get(value)
        if category is None:
            raise ValidationError("Category does not exist.")