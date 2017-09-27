from code.constants.common import X_AXIS, Y_AXIS, VERY_DETERMINED, SOMEWHAT_DETERMINED, NOT_DETERMINED

# Gather a list of entities that intersects with a given entity.
class IntersectionQueryResults:

    def __init__(self):

        # Track the entities that match (i.e. intersect)
        self.entities = []


    # Add an entity to the results
    def add(self, entity):

        self.entities.append(entity)


    # Add a group of entities to the results
    def extend(self, entities):

        self.entities.extend(entities)


    # Filter a given list of entities out of the results
    def filter_out_entities(self, entities):

        # Loop results
        i = 0

        while ( i < len(self.entities) ):

            # If this result is in the list of entities to remove, then remove it...
            if ( self.entities[i] in entities ):

                # Goodbye
                self.entities.pop(i)

            # Otherwise, loop on...
            else:
                i += 1


        # For chaining
        return self


    # Check a list of colliding entities, filtering out any entity that this entity is allowed to overlap with
    #def check_for_entity_exception(self, m, determined, entities, axis):
    def filter_out_by_excepting_entity_on_map(self, excepting_entity, m, determined, axis):

        # Loop through the given list of entities
        i = 0

        # We'll remove the excepted ones...
        while ( i < len(self.entities) ):

            # Convenience
            entity = self.entities[i]

            # Assume that we can except this entity for now
            excepted = True


            # Initial eligibility; if we're not traveling in opposite directions on the relevant axis, then we can't freeze...
            eligible = True

            if ( (axis == X_AXIS) and (excepting_entity.ai_state.last_attempted_lateral_move == entity.ai_state.last_attempted_lateral_move) ):
                eligible = False

            elif ( (axis == Y_AXIS) and (excepting_entity.ai_state.last_attempted_vertical_move == entity.ai_state.last_attempted_vertical_move) ):
                eligible = False



            # If one of the entities is already frozen (i.e. excepted) for the other, then we'll do nothing (i.e. success)
            if ( (excepting_entity == entity.ai_state.ai_frozen_for) or (entity == excepting_entity.ai_state.ai_frozen_for) ):

                # We'll filter this one out
                pass

            # Entities must be one the same axis (at least one same axis); they can't have "crooked" diagonal exceptions
            elif ( (excepting_entity.get_x() != entity.get_x()) and (excepting_entity.get_y() != entity.get_y()) ):

                # Not in line with each other, not parallel
                excepted = False

            # If the excepting entity isn't at all determined to overlap, then just fail the test
            elif (determined == NOT_DETERMINED):

                # Didn't want it bad enough!
                excepted = False


            # Can we, with determination, freeze this enemy; or, have we previous frozen this enemy?
            elif ( (determined == VERY_DETERMINED) and ( (not entity.ai_state.ai_frozen) or (excepting_entity == entity.ai_state.ai_frozen_for) ) and (eligible) ):

                # if we already froze him, then we're good...
                if (entity.ai_state.ai_frozen_for == excepting_entity):

                    # Test succeeds
                    pass

                # Otherwise... we can only freeze him when on the same x-level or same y-level...
                elif ( (excepting_entity.get_x() != entity.get_x()) and (excepting_entity.get_y() != entity.get_y()) ):

                    # I think this is duplicate from 2nd top-level IF test...
                    excepted = False

                # Final confirmation...
                else:

                    # Can we freeze this entity?
                    if ( entity.ai_can_freeze(m, excepting_entity) ):

                        # Make sure to reserve this enemy for the excepting entity (exclusively!)... can't have EVERYONE walking over him...
                        entity.ai_state.ai_frozen = True
                        entity.ai_state.ai_frozen_for = excepting_entity

                    # Can't freeze this enemy right now
                    else:
                        excepted = False


            # If we're only somewhat determined, then we won't freeze any unfrozen dude; we'll only continue if we previously froze him in a moment of high determination
            elif ( (determined == SOMEWHAT_DETERMINED) and (excepting_entity == entity.ai_state.ai_frozen_for) and (excepting_entity.ai_state.last_attempted_lateral_move != entity.ai_state.last_attempted_lateral_move) ):

                # Can this entity freeze at the moment?
                if ( entity.ai_can_freeze(m, excepting_entity) ):

                    # Just for certainty
                    entity.ai_state.ai_frozen = True
                    entity.ai_state.ai_frozen_for = excepting_entity

                # Can't freeze right now
                else:
                    excepted = False

            # No?  Then we need to cancel the move...
            else:
                excepted = False


            # If this entity is excepted from collision, then filter it out...
            if (excepted):

                # Doesn't count
                self.entities.pop(i)

            # Otherwise, keep looping
            else:

                i += 1


        # For chaining
        return self


    # Get the results
    def get_results(self):

        # We should have done all filtering by now
        return self.entities
