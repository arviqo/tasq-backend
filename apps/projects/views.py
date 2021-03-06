# Stdlib imports

# Core Flask imports
from flask import jsonify, request
from flask.views import MethodView

# Third-party app imports
from flask_jwt import jwt_required, current_identity
from sqlalchemy import or_
from sqlalchemy.orm.exc import NoResultFound

# Imports from your apps
from init.database import db
from init.utils import parse_json_to_object

from apps.users.models import User
from apps.projects.models import Project
from apps.projects.schemas import (
    ProjectSchema, ProjectCreateSchema, CollaboratorDeleteSchema
)


__all__ = (
    'ProjectView',
    'CollaboratorView'
)


class ProjectView(MethodView):
    @jwt_required()
    def get(self):
        invited_projects_ids = current_identity\
            .invited_projects.with_entities(Project.id)
        projects = Project.query.filter(
            Project.is_deleted.is_(False)
        ).filter(or_(
            Project.id.in_(invited_projects_ids),
            Project.owner_id == current_identity.id
        )).order_by(Project.created_at.desc())

        data = ProjectSchema(many=True).dump(projects).data
        return jsonify({
            'quantity': projects.count(),
            'results': data
        })

    @jwt_required()
    def post(self):
        json_data = request.get_json()
        result = ProjectCreateSchema().load(json_data)

        if result.errors:
            return jsonify(result.errors), 403

        project = Project()
        parse_json_to_object(project, result.data)
        project.owner = current_identity

        db.session.add(project)
        db.session.commit()

        data = ProjectSchema().dump(project).data
        return jsonify(data)

    @jwt_required()
    def put(self, item_id):
        json_data = request.get_json()
        project = Project.query.get(item_id)
        if project is None:
            return jsonify({'error': 'Project not found.'}), 404

        if current_identity.id == project.owner_id:
            result = ProjectSchema().load(json_data)
        else:
            result = ProjectSchema(exclude=('is_deleted', )).load(json_data)

        if result.errors:
            return jsonify(result.errors), 403

        parse_json_to_object(project, result.data)

        db.session.add(project)
        db.session.commit()

        data = ProjectSchema().dump(project).data
        return jsonify(data)

    @jwt_required()
    def delete(self, item_id):
        project = Project.query.get(item_id)
        if project is None:
            return jsonify({'error': 'Project not found.'}), 404

        if current_identity.id != project.owner_id:
            return jsonify({'error': 'Project not found.'}), 404

        project.is_deleted = True

        db.session.add(project)
        db.session.commit()

        return jsonify({})


class CollaboratorView(MethodView):
    @jwt_required()
    def delete(self):
        json_data = request.get_json()
        result = CollaboratorDeleteSchema().load(json_data)

        if result.errors:
            return jsonify(result.errors), 403

        project = Project.query.get(result.data['project_id'])
        if project is None:
            return jsonify({'error': 'Project not found.'}), 404
        if current_identity.id != project.owner_id:
            return jsonify({'error': 'You should be owner of the project.'}), 403

        try:
            collaborator = project.collaborators.filter(
                User.id == result.data['collaborator_id']
            ).one()
        except NoResultFound:
            return jsonify({'error': 'Invalid collaborator.'}), 403

        project.collaborators.remove(collaborator)

        db.session.add(project)
        db.session.commit()

        return jsonify({})
