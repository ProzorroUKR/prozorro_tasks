from flask_restx import reqparse, inputs

parser_query = reqparse.RequestParser()
parser_query.add_argument("sandbox", type=inputs.boolean)
