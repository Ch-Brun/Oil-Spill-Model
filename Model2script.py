from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterString
from qgis.core import QgsProcessingParameterExpression
from qgis.core import QgsProcessingParameterField
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterFeatureSink
import processing


class OilSpillSecondStageModelFinalVersion(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer('breaklines', 'Houses breaklines polygons', types=[QgsProcessing.TypeVector], defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('depth', 'Depth', types=[QgsProcessing.TypeVectorPoint], defaultValue=None))
        self.addParameter(QgsProcessingParameterString('id', 'id', multiLine=False, defaultValue='id'))
        self.addParameter(QgsProcessingParameterVectorLayer('percedingspillstage', 'Perceding spill stage', types=[QgsProcessing.TypeVectorPoint], defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('perimeter', 'Perimeter', types=[QgsProcessing.TypeVectorPolygon], defaultValue=None))
        self.addParameter(QgsProcessingParameterExpression('temperatureinc', 'Temperature in °C', parentLayerParameterName='', defaultValue='13.7'))
        self.addParameter(QgsProcessingParameterField('timeaffterspillinminutes', 'Time affter spill in minutes', type=QgsProcessingParameterField.Any, parentLayerParameterName='velocityx', allowMultiple=False, defaultValue='5'))
        self.addParameter(QgsProcessingParameterExpression('timemin', 'Minutes after the spill', parentLayerParameterName='', defaultValue=''))
        self.addParameter(QgsProcessingParameterNumber('timespan', 'Timespan between the stages', type=QgsProcessingParameterNumber.Double, minValue=1, maxValue=100, defaultValue=1))
        self.addParameter(QgsProcessingParameterVectorLayer('velocityx', 'Velocity x', types=[QgsProcessing.TypeVectorPoint], defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('velocityy', 'Velocity y', types=[QgsProcessing.TypeVectorPoint], defaultValue=None))
        self.addParameter(QgsProcessingParameterExpression('volumeofthespillinlitres', 'Volume of the spill in litres', parentLayerParameterName='', defaultValue='2000'))
        self.addParameter(QgsProcessingParameterFeatureSink('OutputSecondStage', 'Output second stage', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, defaultValue=None))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(24, model_feedback)
        results = {}
        outputs = {}

        # Gitter (Nächster Nachbar)
        alg_params = {
            'ANGLE': 0,
            'DATA_TYPE': 5,
            'INPUT': parameters['depth'],
            'NODATA': 0,
            'OPTIONS': '',
            'RADIUS_1': 0,
            'RADIUS_2': 0,
            'Z_FIELD': parameters['timeaffterspillinminutes'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['GitterNchsterNachbar'] = processing.run('gdal:gridnearestneighbor', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Gitter (Nächster Nachbar)
        alg_params = {
            'ANGLE': 0,
            'DATA_TYPE': 5,
            'INPUT': parameters['velocityy'],
            'NODATA': 0,
            'OPTIONS': '',
            'RADIUS_1': 0,
            'RADIUS_2': 0,
            'Z_FIELD': parameters['timeaffterspillinminutes'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['GitterNchsterNachbar'] = processing.run('gdal:gridnearestneighbor', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Zufällige Auswahl
        alg_params = {
            'INPUT': parameters['percedingspillstage'],
            'METHOD': 1,
            'NUMBER': QgsExpression('100- floor( (5.91 + 0.045 *@temperatureinc  )*ln(@timemin) - ((5.91 + 0.045 * @temperatureinc )*ln(@timemin-1)))').evaluate()
        }
        outputs['ZuflligeAuswahl'] = processing.run('qgis:randomselection', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Gewählte Objekte exportieren
        alg_params = {
            'INPUT': outputs['ZuflligeAuswahl']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['GewhlteObjekteExportieren'] = processing.run('native:saveselectedfeatures', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # Gitter (Nächster Nachbar)
        alg_params = {
            'ANGLE': 0,
            'DATA_TYPE': 5,
            'INPUT': parameters['velocityx'],
            'NODATA': 0,
            'OPTIONS': '',
            'RADIUS_1': 0,
            'RADIUS_2': 0,
            'Z_FIELD': parameters['timeaffterspillinminutes'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['GitterNchsterNachbar'] = processing.run('gdal:gridnearestneighbor', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Minimale begrenzende Geometrie
        alg_params = {
            'FIELD': None,
            'INPUT': outputs['GewhlteObjekteExportieren']['OUTPUT'],
            'TYPE': 3,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['MinimaleBegrenzendeGeometrie'] = processing.run('qgis:minimumboundinggeometry', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        # Felder überarbeiten
        alg_params = {
            'FIELDS_MAPPING': [{'expression': '"id"', 'length': 10, 'name': 'id', 'precision': 0, 'type': 4}],
            'INPUT': outputs['GewhlteObjekteExportieren']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['FelderBerarbeiten'] = processing.run('qgis:refactorfields', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(7)
        if feedback.isCanceled():
            return {}

        # "Leerwert" füllen
        alg_params = {
            'BAND': 1,
            'DISTANCE': 10,
            'INPUT': outputs['GitterNchsterNachbar']['OUTPUT'],
            'ITERATIONS': 0,
            'MASK_LAYER': None,
            'NO_MASK': False,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['LeerwertFllen'] = processing.run('gdal:fillnodata', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(8)
        if feedback.isCanceled():
            return {}

        # "Leerwert" füllen
        alg_params = {
            'BAND': 1,
            'DISTANCE': 10,
            'INPUT': outputs['GitterNchsterNachbar']['OUTPUT'],
            'ITERATIONS': 0,
            'MASK_LAYER': None,
            'NO_MASK': False,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['LeerwertFllen'] = processing.run('gdal:fillnodata', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(9)
        if feedback.isCanceled():
            return {}

        # Zentroide
        alg_params = {
            'ALL_PARTS': False,
            'INPUT': outputs['MinimaleBegrenzendeGeometrie']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Zentroide'] = processing.run('native:centroids', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(10)
        if feedback.isCanceled():
            return {}

        # Add raster values to features
        alg_params = {
            'GRIDS': [outputs['LeerwertFllen']['OUTPUT'],outputs['LeerwertFllen']['OUTPUT'],outputs['GitterNchsterNachbar']['OUTPUT']],
            'RESAMPLING': 0,
            'SHAPES': parameters['perimeter'],
            'RESULT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['AddRasterValuesToFeatures'] = processing.run('saga:addrastervaluestofeatures', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(11)
        if feedback.isCanceled():
            return {}

        # Attribute nach Position zusammenfügen
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'INPUT': outputs['FelderBerarbeiten']['OUTPUT'],
            'JOIN': outputs['AddRasterValuesToFeatures']['RESULT'],
            'JOIN_FIELDS': None,
            'METHOD': 1,
            'PREDICATE': 0,
            'PREFIX': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['AttributeNachPositionZusammenfgen'] = processing.run('qgis:joinattributesbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(12)
        if feedback.isCanceled():
            return {}

        # Verschieben
        alg_params = {
            'DELTA_M': 0,
            'DELTA_X': QgsProperty.fromExpression('CASE 
WHEN "OUTPUT_2" > 0  THEN 
(sqrt((pi()*1.21^2*(((@volumeofthespillinlitres/1000)^2*9.81*0.1793*((1/60)* @timemin )^1.5)/0.000001139^0.5)^(1/3))/pi()))/60 * sin(azimuth( make_point( @Zentroide_OUTPUT_maxx , @Zentroide_OUTPUT_maxy ), $geometry))*60* @timespan
ELSE 0
END'),
            'DELTA_Y': QgsProperty.fromExpression('CASE 
WHEN "OUTPUT_2" > 0  THEN 
(sqrt((pi()*1.21^2*(((@volumeofthespillinlitres/1000)^2*9.81*0.1793*((1/60)* @timemin )^1.5)/0.000001139^0.5)^(1/3))/pi()))/60 * cos(azimuth( make_point( @Zentroide_OUTPUT_maxx , @Zentroide_OUTPUT_maxy ), $geometry))*60* @timespan
ELSE 0
END'),
            'DELTA_Z': 0,
            'INPUT': outputs['AttributeNachPositionZusammenfgen']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Verschieben'] = processing.run('native:translategeometry', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(13)
        if feedback.isCanceled():
            return {}

        # Felder überarbeiten
        alg_params = {
            'FIELDS_MAPPING': [{'expression': '"id"', 'length': 10, 'name': 'id', 'precision': 0, 'type': 4}],
            'INPUT': outputs['Verschieben']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['FelderBerarbeiten'] = processing.run('qgis:refactorfields', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(14)
        if feedback.isCanceled():
            return {}

        # Attribute nach Position zusammenfügen
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'INPUT': outputs['FelderBerarbeiten']['OUTPUT'],
            'JOIN': outputs['AddRasterValuesToFeatures']['RESULT'],
            'JOIN_FIELDS': None,
            'METHOD': 0,
            'PREDICATE': 0,
            'PREFIX': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['AttributeNachPositionZusammenfgen'] = processing.run('qgis:joinattributesbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(15)
        if feedback.isCanceled():
            return {}

        # Verschieben
        alg_params = {
            'DELTA_M': 0,
            'DELTA_X': QgsProperty.fromExpression('CASE 
WHEN "OUTPUT_2" > 0.001 
THEN "OUTPUT" * 60 *  @timespan
ELSE 0
END'),
            'DELTA_Y': QgsProperty.fromExpression('CASE 
WHEN "OUTPUT_2" > 0.001 
THEN "OUTPUT_1" * 60 *  @timespan
ELSE 0
END'),
            'DELTA_Z': 0,
            'INPUT': outputs['AttributeNachPositionZusammenfgen']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Verschieben'] = processing.run('native:translategeometry', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(16)
        if feedback.isCanceled():
            return {}

        # Minimale begrenzende Geometrie
        alg_params = {
            'FIELD': None,
            'INPUT': outputs['Verschieben']['OUTPUT'],
            'TYPE': 3,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['MinimaleBegrenzendeGeometrie'] = processing.run('qgis:minimumboundinggeometry', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(17)
        if feedback.isCanceled():
            return {}

        # Difference
        alg_params = {
            'A': outputs['MinimaleBegrenzendeGeometrie']['OUTPUT'],
            'B': parameters['breaklines'],
            'SPLIT': True,
            'RESULT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Difference'] = processing.run('saga:difference', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(18)
        if feedback.isCanceled():
            return {}

        # Nach Position extrahieren
        alg_params = {
            'INPUT': outputs['Verschieben']['OUTPUT'],
            'INTERSECT': parameters['breaklines'],
            'PREDICATE': 2,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['NachPositionExtrahieren'] = processing.run('native:extractbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(19)
        if feedback.isCanceled():
            return {}

        # Attribute nach Position zusammenfügen
        alg_params = {
            'DISCARD_NONMATCHING': True,
            'INPUT': outputs['Verschieben']['OUTPUT'],
            'JOIN': parameters['breaklines'],
            'JOIN_FIELDS': None,
            'METHOD': 1,
            'PREDICATE': 5,
            'PREFIX': ''
        }
        outputs['AttributeNachPositionZusammenfgen'] = processing.run('qgis:joinattributesbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(20)
        if feedback.isCanceled():
            return {}

        # Zufällige Punkte in Polygonen
        alg_params = {
            'EXPRESSION': outputs['AttributeNachPositionZusammenfgen']['JOINED_COUNT'],
            'INPUT': outputs['Difference']['RESULT'],
            'MIN_DISTANCE': 0,
            'STRATEGY': 0,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ZuflligePunkteInPolygonen'] = processing.run('qgis:randompointsinsidepolygons', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(21)
        if feedback.isCanceled():
            return {}

        # Duplikate nach Attribut löschen
        alg_params = {
            'FIELDS': parameters['id'],
            'INPUT': outputs['ZuflligePunkteInPolygonen']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['DuplikateNachAttributLschen'] = processing.run('native:removeduplicatesbyattribute', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(22)
        if feedback.isCanceled():
            return {}

        # Felder überarbeiten
        alg_params = {
            'FIELDS_MAPPING': [{'expression': '"id"', 'length': 10, 'name': 'id', 'precision': 0, 'type': 4}],
            'INPUT': outputs['DuplikateNachAttributLschen']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['FelderBerarbeiten'] = processing.run('qgis:refactorfields', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(23)
        if feedback.isCanceled():
            return {}

        # Vektorlayer zusammenführen
        alg_params = {
            'CRS': None,
            'LAYERS': [outputs['NachPositionExtrahieren']['OUTPUT'],outputs['FelderBerarbeiten']['OUTPUT']],
            'OUTPUT': parameters['OutputSecondStage']
        }
        outputs['VektorlayerZusammenfhren'] = processing.run('native:mergevectorlayers', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['OutputSecondStage'] = outputs['VektorlayerZusammenfhren']['OUTPUT']
        return results

    def name(self):
        return '1oil spill second stage model final version'

    def displayName(self):
        return '1oil spill second stage model final version'

    def group(self):
        return ''

    def groupId(self):
        return ''

    def createInstance(self):
        return OilSpillSecondStageModelFinalVersion()
